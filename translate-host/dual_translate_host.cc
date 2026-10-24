// Copyright 2026 Dual contributors.
// Created on 2026-10-24. Licensed under GPL-3.0; see the LICENSE file.
//
// The native messaging host behind "Dual Page Translate". The browser starts
// it when the extension connects and talks to it over stdin and stdout. It
// downloads the translation model once, checks it against a fixed SHA-256,
// and runs it with llama.cpp on this computer: the text it is given never
// leaves the computer.
//
// Messages from the extension:
//   {"type":"hello"}                          -> {"type":"hello", ...status}
//   {"type":"download"}                       -> {"type":"download", ...}*
//   {"type":"cancelDownload"}
//   {"type":"generate","id","system","user","maxTokens"}
//                                             -> {"type":"delta","id","text"}*
//                                                {"type":"done","id","text"}
//                                             or {"type":"error","id","error"}
//   {"type":"cancel","id"}
// The host exits when the extension disconnects.

#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include <curl/curl.h>

#include "llama.h"
#include "nlohmann/json.hpp"
#include "sha256.h"

namespace dual_translate {
namespace {

using json = nlohmann::json;
using Clock = std::chrono::steady_clock;

constexpr char kHostVersion[] = "2";

// How many requests are translated at once (see Translator): on a GPU, more
// at once go much faster in all; on a CPU, hardly. DUAL_TRANSLATE_PARALLEL
// sets another number, for measuring.
int Parallel() {
  static const int parallel = [] {
    const char* set = std::getenv("DUAL_TRANSLATE_PARALLEL");
    const int number = set ? std::atoi(set) : 0;
#if defined(__APPLE__)
    const int usual = 8;
#else
    const int usual = 2;
#endif
    return number >= 1 && number <= 16 ? number : usual;
  }();
  return parallel;
}

// The model: Gemma 4 E4B (Apache-2.0), 4-bit, from a fixed commit.
constexpr char kModelName[] = "Gemma 4 E4B";
constexpr char kModelFile[] = "gemma-4-E4B-it-Q4_K_M.gguf";
constexpr char kModelUrl[] =
    "https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/"
    "bfc15c382204943c3a8fff0c750b94ae2364d7a3/gemma-4-E4B-it-Q4_K_M.gguf";
constexpr uint64_t kModelSize = 4977171584ull;
constexpr char kModelSha256[] =
    "85a896a047553e842f25297ee5b031d64ff30147d9c4af17b1e4b394cd1fab87";

// Room left on the disk after the download, so that it never fills it up.
constexpr uint64_t kSpareSpace = 1ull << 30;


// ---------------------------------------------------------------------------
// Messages

std::mutex g_send_mutex;

// With DUAL_TRANSLATE_DEBUG set, how the requests went goes to stderr (the
// browser's log).
bool Debugging() {
  static const bool debugging = std::getenv("DUAL_TRANSLATE_DEBUG") != nullptr;
  return debugging;
}

double Seconds() {
  static const auto start = Clock::now();
  return std::chrono::duration<double>(Clock::now() - start).count();
}

void Send(const json& message) {
  const std::string text =
      message.dump(-1, ' ', false, json::error_handler_t::replace);
  const uint32_t size = static_cast<uint32_t>(text.size());
  std::lock_guard<std::mutex> lock(g_send_mutex);
  std::fwrite(&size, sizeof(size), 1, stdout);
  std::fwrite(text.data(), 1, text.size(), stdout);
  std::fflush(stdout);
}

bool Receive(json* message) {
  uint32_t size;
  if (std::fread(&size, sizeof(size), 1, stdin) != 1 || size > (64u << 20)) {
    return false;
  }
  std::string text(size, '\0');
  if (std::fread(text.data(), 1, size, stdin) != size) {
    return false;
  }
  *message = json::parse(text, nullptr, /*allow_exceptions=*/false);
  return true;
}

// ---------------------------------------------------------------------------
// Files

std::string ModelDirectory() {
  if (const char* directory = std::getenv("DUAL_TRANSLATION_DIR");
      directory && *directory) {
    return directory;
  }
  const char* home = std::getenv("HOME");
  const std::string home_directory = home ? home : "";
#if defined(__APPLE__)
  return home_directory + "/Library/Application Support/Dual Translation";
#else
  const char* data = std::getenv("XDG_DATA_HOME");
  return (data && *data ? std::string(data) : home_directory + "/.local/share") +
         "/dual-translation";
#endif
}

std::string ModelPath() {
  return ModelDirectory() + "/" + kModelFile;
}

std::string PartialPath() {
  return ModelPath() + ".part";
}

bool MakeDirectories(const std::string& path) {
  for (size_t at = 1; at <= path.size(); ++at) {
    if (at == path.size() || path[at] == '/') {
      const std::string part = path.substr(0, at);
      if (mkdir(part.c_str(), 0755) != 0 && errno != EEXIST) {
        return false;
      }
    }
  }
  return true;
}

// The size of the file at `path`, or -1 if there is none.
int64_t FileSize(const std::string& path) {
  struct stat info;
  return stat(path.c_str(), &info) == 0 ? info.st_size : -1;
}

// Free space on the disk that holds `path` or its nearest existing parent.
uint64_t FreeSpace(std::string path) {
  struct statvfs info;
  while (!path.empty()) {
    if (statvfs(path.c_str(), &info) == 0) {
      return static_cast<uint64_t>(info.f_bavail) * info.f_frsize;
    }
    path = path.substr(0, path.rfind('/'));
  }
  return 0;
}

bool ModelReady() {
  return FileSize(ModelPath()) == static_cast<int64_t>(kModelSize);
}

json Status() {
  const int64_t partial = FileSize(PartialPath());
  return {
      {"hostVersion", kHostVersion},
      // How many requests it translates at once.
      {"parallel", Parallel()},
#if defined(__APPLE__)
      {"accelerator", "metal"},
#else
      {"accelerator", "cpu"},
#endif
      {"model",
       {{"name", kModelName},
        {"state", ModelReady() ? "ready" : partial > 0 ? "partial" : "missing"},
        {"bytes", ModelReady() ? kModelSize : std::max<int64_t>(partial, 0)},
        {"total", kModelSize},
        {"directory", ModelDirectory()}}},
      {"freeSpace", FreeSpace(ModelDirectory())},
  };
}

// ---------------------------------------------------------------------------
// Download

// libcurl, opened at run time so that the host still translates where it is
// missing (some Linux systems).
struct Curl {
  CURLcode (*global_init)(long);
  CURL* (*easy_init)();
  CURLcode (*easy_setopt)(CURL*, CURLoption, ...);
  CURLcode (*easy_perform)(CURL*);
  CURLcode (*easy_getinfo)(CURL*, CURLINFO, ...);
  void (*easy_cleanup)(CURL*);

  static const Curl* Get() {
    static const Curl* curl = [] () -> const Curl* {
      static const char* const kNames[] = {
#if defined(__APPLE__)
          "/usr/lib/libcurl.4.dylib",
#else
          "libcurl.so.4",
          "libcurl-gnutls.so.4",
#endif
      };
      for (const char* name : kNames) {
        void* library = dlopen(name, RTLD_NOW | RTLD_LOCAL);
        if (!library) {
          continue;
        }
        static Curl loaded;
        loaded.global_init = reinterpret_cast<decltype(loaded.global_init)>(
            dlsym(library, "curl_global_init"));
        loaded.easy_init = reinterpret_cast<decltype(loaded.easy_init)>(
            dlsym(library, "curl_easy_init"));
        loaded.easy_setopt = reinterpret_cast<decltype(loaded.easy_setopt)>(
            dlsym(library, "curl_easy_setopt"));
        loaded.easy_perform = reinterpret_cast<decltype(loaded.easy_perform)>(
            dlsym(library, "curl_easy_perform"));
        loaded.easy_getinfo = reinterpret_cast<decltype(loaded.easy_getinfo)>(
            dlsym(library, "curl_easy_getinfo"));
        loaded.easy_cleanup = reinterpret_cast<decltype(loaded.easy_cleanup)>(
            dlsym(library, "curl_easy_cleanup"));
        if (loaded.global_init && loaded.easy_init && loaded.easy_setopt &&
            loaded.easy_perform && loaded.easy_getinfo && loaded.easy_cleanup &&
            loaded.global_init(CURL_GLOBAL_DEFAULT) == CURLE_OK) {
          return &loaded;
        }
      }
      return nullptr;
    }();
    return curl;
  }
};

class Downloader {
 public:
  ~Downloader() { Stop(); }

  void Start() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (running_) {
      return;
    }
    if (thread_.joinable()) {
      thread_.join();
    }
    cancel_ = false;
    running_ = true;
    thread_ = std::thread([this] {
      Run();
      running_ = false;
    });
  }

  void Cancel() { cancel_ = true; }

  void Stop() {
    cancel_ = true;
    std::lock_guard<std::mutex> lock(mutex_);
    if (thread_.joinable()) {
      thread_.join();
    }
  }

 private:
  struct Transfer {
    FILE* file;
    uint64_t start;
    Downloader* downloader;
    Clock::time_point last_report;
  };

  static size_t Write(char* data, size_t size, size_t count, void* user) {
    auto* transfer = static_cast<Transfer*>(user);
    return std::fwrite(data, size, count, transfer->file) * size;
  }

  static int Progress(void* user, curl_off_t, curl_off_t now, curl_off_t,
                      curl_off_t) {
    auto* transfer = static_cast<Transfer*>(user);
    if (transfer->downloader->cancel_) {
      return 1;
    }
    const auto time = Clock::now();
    if (time - transfer->last_report > std::chrono::milliseconds(500)) {
      transfer->last_report = time;
      Send({{"type", "download"},
            {"state", "running"},
            {"bytes", transfer->start + static_cast<uint64_t>(now)},
            {"total", kModelSize}});
    }
    return 0;
  }

  static void Fail(const std::string& error, json extra = json::object()) {
    extra["type"] = "download";
    extra["state"] = "error";
    extra["error"] = error;
    Send(extra);
  }

  void Run() {
    if (ModelReady()) {
      Send({{"type", "download"}, {"state", "done"}});
      return;
    }
    const Curl* curl = Curl::Get();
    if (!curl) {
      Fail("no_curl");
      return;
    }
    if (!MakeDirectories(ModelDirectory())) {
      Fail("folder");
      return;
    }
    const std::string partial = PartialPath();
    if (FileSize(partial) > static_cast<int64_t>(kModelSize)) {
      std::remove(partial.c_str());
    }

    // A dropped connection is picked up where it stopped, a few times.
    CURLcode result = CURLE_OK;
    long http_status = 0;
    for (int attempt = 0; attempt < 4; ++attempt) {
      const uint64_t have = std::max<int64_t>(FileSize(partial), 0);
      if (have == kModelSize) {
        break;
      }
      const uint64_t needed = kModelSize - have + kSpareSpace;
      const uint64_t free_space = FreeSpace(ModelDirectory());
      if (free_space < needed) {
        Fail("space", {{"needed", needed}, {"free", free_space}});
        return;
      }
      FILE* file = std::fopen(partial.c_str(), "ab");
      if (!file) {
        Fail("folder");
        return;
      }
      Transfer transfer{file, have, this, Clock::now()};
      CURL* handle = curl->easy_init();
      curl->easy_setopt(handle, CURLOPT_URL, kModelUrl);
      curl->easy_setopt(handle, CURLOPT_FOLLOWLOCATION, 1L);
      curl->easy_setopt(handle, CURLOPT_FAILONERROR, 1L);
      curl->easy_setopt(handle, CURLOPT_USERAGENT, "Dual-Translate/1");
      curl->easy_setopt(handle, CURLOPT_CONNECTTIMEOUT, 30L);
      curl->easy_setopt(handle, CURLOPT_LOW_SPEED_LIMIT, 1024L);
      curl->easy_setopt(handle, CURLOPT_LOW_SPEED_TIME, 60L);
      curl->easy_setopt(handle, CURLOPT_RESUME_FROM_LARGE,
                        static_cast<curl_off_t>(have));
      curl->easy_setopt(handle, CURLOPT_WRITEFUNCTION, &Downloader::Write);
      curl->easy_setopt(handle, CURLOPT_WRITEDATA, &transfer);
      curl->easy_setopt(handle, CURLOPT_NOPROGRESS, 0L);
      curl->easy_setopt(handle, CURLOPT_XFERINFOFUNCTION,
                        &Downloader::Progress);
      curl->easy_setopt(handle, CURLOPT_XFERINFODATA, &transfer);
      result = curl->easy_perform(handle);
      http_status = 0;
      curl->easy_getinfo(handle, CURLINFO_RESPONSE_CODE, &http_status);
      curl->easy_cleanup(handle);
      const bool write_failed = std::fclose(file) != 0;
      if (cancel_ || result == CURLE_ABORTED_BY_CALLBACK) {
        Send({{"type", "download"},
              {"state", "canceled"},
              {"bytes", std::max<int64_t>(FileSize(partial), 0)},
              {"total", kModelSize}});
        return;
      }
      if (write_failed || result == CURLE_WRITE_ERROR) {
        Fail("write");
        return;
      }
      if (result == CURLE_OK) {
        break;
      }
      // A server that will not resume: start over.
      if (http_status == 416 || result == CURLE_RANGE_ERROR) {
        std::remove(partial.c_str());
      }
      std::this_thread::sleep_for(std::chrono::seconds(2 << attempt));
    }
    if (FileSize(partial) != static_cast<int64_t>(kModelSize)) {
      Fail("network", {{"code", static_cast<int>(result)},
                       {"status", http_status}});
      return;
    }

    Send({{"type", "download"}, {"state", "verifying"}, {"bytes", 0},
          {"total", kModelSize}});
    auto last_report = Clock::now();
    const std::string digest =
        Sha256OfFile(partial, cancel_, [&](uint64_t done) {
          if (Clock::now() - last_report > std::chrono::milliseconds(500)) {
            last_report = Clock::now();
            Send({{"type", "download"}, {"state", "verifying"},
                  {"bytes", done}, {"total", kModelSize}});
          }
        });
    if (cancel_) {
      Send({{"type", "download"}, {"state", "canceled"},
            {"bytes", kModelSize}, {"total", kModelSize}});
      return;
    }
    if (digest != kModelSha256) {
      std::remove(partial.c_str());
      Fail("hash");
      return;
    }
    if (std::rename(partial.c_str(), ModelPath().c_str()) != 0) {
      Fail("write");
      return;
    }
    Send({{"type", "download"}, {"state", "done"}});
  }

  std::mutex mutex_;
  std::thread thread_;
  std::atomic<bool> cancel_{false};
  std::atomic<bool> running_{false};
};

// ---------------------------------------------------------------------------
// Translation

struct Job {
  std::string id;
  std::string system;
  std::string user;
  int max_tokens;
};

// How much of `text` ends on a whole UTF-8 character.
size_t CompleteUtf8Length(const std::string& text) {
  size_t end = text.size();
  for (size_t back = 1; back <= 4 && back <= text.size(); ++back) {
    const auto byte = static_cast<unsigned char>(text[text.size() - back]);
    if ((byte & 0xC0) == 0x80) {
      continue;  // A continuation byte: look further back.
    }
    const size_t length = byte < 0x80             ? 1
                          : (byte & 0xE0) == 0xC0 ? 2
                          : (byte & 0xF0) == 0xE0 ? 3
                                                  : 4;
    if (back < length) {
      end = text.size() - back;
    }
    break;
  }
  return end;
}

// Translates several requests at once. Each is a sequence of its own in one
// llama.cpp context, and every step decodes the next token of all of them in
// one batch: the GPU has room for that, so a page's paragraphs, sent as a few
// requests, come back several times faster than one request after another.
class Translator {
 public:
  const int sequences_ = Parallel();
  // The most one request may take, and all of them together.
  static constexpr int kTokensPerSequence = 8192;
  static constexpr int kContextTokens = 65536;
  // Instructions already read, kept to be copied into new requests (the
  // sequences after the requests' own).
  static constexpr int kTemplates = 2;

  Translator() : thread_([this] { Run(); }) {}

  ~Translator() {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      quit_ = true;
    }
    wake_.notify_all();
    thread_.join();
    if (context_) {
      llama_free(context_);
    }
    if (model_) {
      llama_model_free(model_);
    }
  }

  void Add(Job job) {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      jobs_.push_back(std::move(job));
    }
    wake_.notify_all();
  }

  void Cancel(const std::string& id) {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      canceled_.insert(id);
    }
    wake_.notify_all();
  }

 private:
  // A request being translated.
  struct Active {
    Job job;
    int sequence;
    int position;     // Tokens in this sequence's memory.
    int max_tokens;
    int made = 0;
    std::vector<llama_token> prompt;  // Still to be read, at the start.
    llama_token next = 0;             // Chosen, not yet decoded.
    std::string text;
    size_t sent = 0;
    Clock::time_point last_send;
  };

  bool TakeCanceled(const std::string& id) {
    std::lock_guard<std::mutex> lock(mutex_);
    return canceled_.erase(id) > 0;
  }

  void Run() {
    std::vector<Active> active;
    for (;;) {
      std::vector<Job> starting;
      {
        std::unique_lock<std::mutex> lock(mutex_);
        wake_.wait(lock, [&] { return quit_ || !jobs_.empty() || !active.empty(); });
        if (quit_) {
          return;
        }
        while (!jobs_.empty() &&
               active.size() + starting.size() < static_cast<size_t>(sequences_)) {
          Job job = std::move(jobs_.front());
          jobs_.pop_front();
          if (canceled_.erase(job.id)) {
            Send({{"type", "error"}, {"id", job.id}, {"error", "canceled"}});
            continue;
          }
          starting.push_back(std::move(job));
        }
      }
      copied_this_round_.clear();
      for (Job& job : starting) {
        Start(std::move(job), active);
      }
      if (!active.empty()) {
        Step(active);
      }
    }
  }

  bool Load() {
    if (context_) {
      return true;
    }
    if (!ModelReady()) {
      return false;
    }
    Send({{"type", "loading"}});
    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = 999;
    model_ = llama_model_load_from_file(ModelPath().c_str(), model_params);
    if (!model_) {
      return false;
    }
    llama_context_params context_params = llama_context_default_params();
    context_params.n_ctx = kContextTokens;
    context_params.n_seq_max = sequences_ + kTemplates;
    // One memory for all the sequences. With a part of its own for each, the
    // steps got slower and slower as requests came and went (twice as slow
    // after 30 requests); shared, they stay as fast, and the instructions
    // copied from a template are shared rather than copied.
    context_params.kv_unified = true;
    // The sliding-window layers keep only their window, not the whole
    // context: as fast here, and about 1.6 GB less memory.
    context_params.swa_full = false;
    context_params.n_batch = 4096;
    context_params.no_perf = true;
    const int threads =
        std::max(1u, std::min(8u, std::thread::hardware_concurrency()));
    context_params.n_threads = threads;
    context_params.n_threads_batch = threads;
    context_ = llama_init_from_model(model_, context_params);
    if (!context_) {
      llama_model_free(model_);
      model_ = nullptr;
      return false;
    }
    return true;
  }

  // The most likely next token after row `row` of the last batch: the
  // translation takes no chances. (llama.cpp's greedy sampler gives the same
  // token, but first builds a table of all 262,144 candidates, which for six
  // requests took about as long as the decoding.)
  llama_token MostLikely(int row) {
    const float* logits = llama_get_logits_ith(context_, row);
    const int count = llama_vocab_n_tokens(llama_model_get_vocab(model_));
    return static_cast<llama_token>(std::max_element(logits, logits + count) - logits);
  }

  struct Template {
    std::string instructions;
    int sequence;
    int length = 0;
    uint64_t used = 0;
  };

  std::vector<llama_token> Tokenize(const std::string& text, bool first) {
    const llama_vocab* vocab = llama_model_get_vocab(model_);
    std::vector<llama_token> tokens(text.size() + 16);
    const int count = llama_tokenize(
        vocab, text.data(), static_cast<int32_t>(text.size()), tokens.data(),
        static_cast<int32_t>(tokens.size()), /*add_special=*/first,
        /*parse_special=*/true);
    tokens.resize(std::max(count, 0));
    return tokens;
  }

  // The template holding `instructions` already read, reading them into the
  // least recently used one if need be; null if that cannot be done now (a
  // template copied from in this round is not replaced: the copy is made at
  // the next decode).
  const Template* TemplateFor(const std::string& instructions) {
    if (templates_.empty()) {
      for (int i = 0; i < kTemplates; ++i) {
        templates_.push_back({"", sequences_ + i});
      }
    }
    for (Template& t : templates_) {
      if (t.length && t.instructions == instructions) {
        t.used = ++uses_;
        copied_this_round_.insert(t.sequence);
        return &t;
      }
    }
    Template* oldest = nullptr;
    for (Template& t : templates_) {
      if (!copied_this_round_.count(t.sequence) && (!oldest || t.used < oldest->used)) {
        oldest = &t;
      }
    }
    if (!oldest) {
      return nullptr;
    }
    const std::vector<llama_token> tokens = Tokenize(instructions, /*first=*/true);
    if (tokens.empty() || tokens.size() > static_cast<size_t>(llama_n_batch(context_))) {
      return nullptr;
    }
    llama_memory_seq_rm(llama_get_memory(context_), oldest->sequence, -1, -1);
    oldest->length = 0;
    llama_batch batch = llama_batch_init(static_cast<int32_t>(tokens.size()), 0, 1);
    for (size_t i = 0; i < tokens.size(); ++i) {
      batch.token[i] = tokens[i];
      batch.pos[i] = static_cast<int>(i);
      batch.n_seq_id[i] = 1;
      batch.seq_id[i][0] = oldest->sequence;
      batch.logits[i] = false;
    }
    batch.n_tokens = static_cast<int32_t>(tokens.size());
    const bool read = llama_decode(context_, batch) == 0;
    llama_batch_free(batch);
    if (!read) {
      return nullptr;
    }
    oldest->instructions = instructions;
    oldest->length = static_cast<int>(tokens.size());
    oldest->used = ++uses_;
    copied_this_round_.insert(oldest->sequence);
    return oldest;
  }

  // Takes a request on in a free sequence. Its prompt is read in the next
  // step, together with the tokens of the others.
  void Start(Job job, std::vector<Active>& active) {
    if (!Load()) {
      Send({{"type", "error"},
            {"id", job.id},
            {"error", ModelReady() ? "load" : "no_model"}});
      return;
    }
    int sequence = 0;
    while (std::any_of(active.begin(), active.end(), [&](const Active& other) {
      return other.sequence == sequence;
    })) {
      ++sequence;
    }
    // The instructions come from a template; only the rest is read here.
    const std::string instructions = "<|turn>system\n" + job.system + "<turn|>\n";
    const std::string rest =
        "<|turn>user\n" + job.user + "<turn|>\n<|turn>model\n";
    const Template* prepared = TemplateFor(instructions);
    std::vector<llama_token> tokens =
        Tokenize(prepared ? rest : instructions + rest, /*first=*/!prepared);
    const int start = prepared ? prepared->length : 0;
    const int count = start + static_cast<int>(tokens.size());
    const int max_tokens =
        std::min(job.max_tokens, kTokensPerSequence - count - 8);
    if (tokens.empty() || max_tokens < 16 ||
        tokens.size() > static_cast<size_t>(llama_n_batch(context_))) {
      Send({{"type", "error"}, {"id", job.id}, {"error", "too_long"}});
      return;
    }
    if (Debugging()) {
      std::fprintf(stderr, "[dual-translate] %.2f start %s seq %d prompt %d (%d read) active %zu\n", Seconds(),
                   job.id.c_str(), sequence, count, static_cast<int>(tokens.size()), active.size() + 1);
    }
    llama_memory_t memory = llama_get_memory(context_);
    llama_memory_seq_rm(memory, sequence, -1, -1);
    if (prepared) {
      llama_memory_seq_cp(memory, prepared->sequence, sequence, -1, -1);
    }
    Active started{std::move(job), sequence, start, max_tokens};
    started.prompt = std::move(tokens);
    started.last_send = Clock::now();
    active.push_back(std::move(started));
  }

  void Finish(Active& done, bool finished) {
    if (Debugging()) {
      std::fprintf(stderr, "[dual-translate] %.2f done %s made %d\n", Seconds(), done.job.id.c_str(), done.made);
    }
    llama_memory_seq_rm(llama_get_memory(context_), done.sequence, -1, -1);
    Send({{"type", "done"},
          {"id", done.job.id},
          {"text", done.text},
          {"finished", finished}});
  }

  // Takes in the chosen token of every request, then decodes them together,
  // with the prompts of requests just started, and chooses the next ones.
  void Step(std::vector<Active>& active) {
    const llama_vocab* vocab = llama_model_get_vocab(model_);
    std::vector<Active> going;
    for (Active& a : active) {
      if (TakeCanceled(a.job.id)) {
        llama_memory_seq_rm(llama_get_memory(context_), a.sequence, -1, -1);
        Send({{"type", "error"}, {"id", a.job.id}, {"error", "canceled"}});
        continue;
      }
      if (!a.prompt.empty()) {
        going.push_back(std::move(a));
        continue;
      }
      if (llama_vocab_is_eog(vocab, a.next)) {
        Finish(a, true);
        continue;
      }
      char piece[256];
      const int length = llama_token_to_piece(vocab, a.next, piece,
                                              sizeof(piece), 0, false);
      if (length > 0) {
        a.text.append(piece, length);
      }
      if (Clock::now() - a.last_send > std::chrono::milliseconds(100)) {
        const size_t complete = CompleteUtf8Length(a.text);
        if (complete > a.sent) {
          Send({{"type", "delta"},
                {"id", a.job.id},
                {"text", a.text.substr(a.sent, complete - a.sent)}});
          a.sent = complete;
        }
        a.last_send = Clock::now();
      }
      if (++a.made >= a.max_tokens) {
        Finish(a, false);
        continue;
      }
      going.push_back(std::move(a));
    }
    active = std::move(going);
    if (active.empty()) {
      return;
    }

    // One batch: a token for each request under way, and whole prompts for
    // as many new ones as fit. A prompt that does not fit waits a step.
    const int capacity = static_cast<int>(llama_n_batch(context_));
    llama_batch batch = llama_batch_init(capacity, 0, 1);
    std::vector<int> row(active.size(), -1);
    auto add = [&](llama_token token, int position, int sequence, bool logits) {
      const int k = batch.n_tokens++;
      batch.token[k] = token;
      batch.pos[k] = position;
      batch.n_seq_id[k] = 1;
      batch.seq_id[k][0] = sequence;
      batch.logits[k] = logits;
      return k;
    };
    for (size_t i = 0; i < active.size(); ++i) {
      if (active[i].prompt.empty()) {
        row[i] = add(active[i].next, active[i].position, active[i].sequence, true);
      }
    }
    for (size_t i = 0; i < active.size(); ++i) {
      Active& a = active[i];
      if (a.prompt.empty() ||
          batch.n_tokens + static_cast<int>(a.prompt.size()) > capacity) {
        continue;
      }
      for (size_t t = 0; t < a.prompt.size(); ++t) {
        row[i] = add(a.prompt[t], a.position + static_cast<int>(t), a.sequence,
                     t + 1 == a.prompt.size());
      }
    }
    const auto before_decode = Clock::now();
    const int decoded = llama_decode(context_, batch);
    if (Debugging()) {
      // Every 50 steps: how long a step took, by kind.
      const double ms = std::chrono::duration<double, std::milli>(Clock::now() - before_decode).count();
      const bool reading = batch.n_tokens > static_cast<int>(active.size());
      step_ms_[reading] += ms;
      step_count_[reading] += 1;
      step_rows_ += static_cast<int>(active.size());
      if (step_count_[0] + step_count_[1] == 50) {
        std::fprintf(stderr, "[dual-translate] %.2f steps: %d decoding %.1f ms avg, %d reading %.1f ms avg, %.1f requests avg\n",
                     Seconds(), step_count_[0], step_count_[0] ? step_ms_[0] / step_count_[0] : 0.0, step_count_[1],
                     step_count_[1] ? step_ms_[1] / step_count_[1] : 0.0, step_rows_ / 50.0);
        step_ms_[0] = step_ms_[1] = 0;
        step_count_[0] = step_count_[1] = 0;
        step_rows_ = 0;
      }
    }
    if (decoded != 0) {
      for (Active& a : active) {
        llama_memory_seq_rm(llama_get_memory(context_), a.sequence, -1, -1);
        Send({{"type", "error"}, {"id", a.job.id}, {"error", "decode"}});
      }
      active.clear();
    } else {
      for (size_t i = 0; i < active.size(); ++i) {
        Active& a = active[i];
        if (row[i] < 0) {
          continue;
        }
        a.next = MostLikely(row[i]);
        if (a.prompt.empty()) {
          ++a.position;
        } else {
          a.position += static_cast<int>(a.prompt.size());
          a.prompt.clear();
        }
      }
    }
    llama_batch_free(batch);
  }

  std::mutex mutex_;
  std::condition_variable wake_;
  std::deque<Job> jobs_;
  std::set<std::string> canceled_;
  bool quit_ = false;
  llama_model* model_ = nullptr;
  llama_context* context_ = nullptr;
  std::vector<Template> templates_;
  double step_ms_[2] = {0, 0};
  int step_count_[2] = {0, 0};
  int step_rows_ = 0;
  std::set<int> copied_this_round_;
  uint64_t uses_ = 0;
  std::thread thread_;
};

void QuietLog(ggml_log_level, const char*, void*) {}

}  // namespace
}  // namespace dual_translate

int main() {
  using namespace dual_translate;
  // stdout carries the messages; anything else printed would break them.
  if (!std::getenv("DUAL_TRANSLATE_DEBUG")) {
    llama_log_set(QuietLog, nullptr);
  }
  llama_backend_init();

  Downloader downloader;
  Translator translator;
  json message;
  while (Receive(&message)) {
    if (!message.is_object()) {
      continue;
    }
    const std::string type = message.value("type", "");
    if (type == "hello") {
      json reply = Status();
      reply["type"] = "hello";
      Send(reply);
    } else if (type == "download") {
      downloader.Start();
    } else if (type == "cancelDownload") {
      downloader.Cancel();
    } else if (type == "generate") {
      translator.Add({message.value("id", ""), message.value("system", ""),
                      message.value("user", ""),
                      message.value("maxTokens", 2048)});
    } else if (type == "cancel") {
      translator.Cancel(message.value("id", ""));
    }
  }
  downloader.Stop();
  return 0;
}
