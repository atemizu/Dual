// Copyright 2026 Dual contributors.
// Created on 2026-10-24. Licensed under GPL-3.0; see the LICENSE file.
//
// SHA-256 of a file, to check the downloaded model. macOS has a fast one in
// CommonCrypto; elsewhere this is the plain FIPS 180-4 algorithm.

#ifndef DUAL_TRANSLATE_HOST_SHA256_H_
#define DUAL_TRANSLATE_HOST_SHA256_H_

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#if defined(__APPLE__)
#include <CommonCrypto/CommonDigest.h>
#endif

namespace dual_translate {

#if !defined(__APPLE__)
class Sha256 {
 public:
  void Update(const uint8_t* data, size_t size) {
    length_ += size;
    while (size > 0) {
      const size_t take = std::min(size, sizeof(block_) - used_);
      std::copy(data, data + take, block_ + used_);
      used_ += take;
      data += take;
      size -= take;
      if (used_ == sizeof(block_)) {
        Compress(block_);
        used_ = 0;
      }
    }
  }

  void Final(uint8_t out[32]) {
    const uint64_t bits = length_ * 8;
    const uint8_t pad = 0x80;
    Update(&pad, 1);
    const uint8_t zero = 0;
    while (used_ != 56) {
      Update(&zero, 1);
    }
    uint8_t size_bytes[8];
    for (int i = 0; i < 8; ++i) {
      size_bytes[i] = static_cast<uint8_t>(bits >> (56 - 8 * i));
    }
    Update(size_bytes, 8);
    for (int i = 0; i < 8; ++i) {
      for (int j = 0; j < 4; ++j) {
        out[i * 4 + j] = static_cast<uint8_t>(state_[i] >> (24 - 8 * j));
      }
    }
  }

 private:
  static uint32_t Rotate(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }

  void Compress(const uint8_t* p) {
    static constexpr uint32_t k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
        0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
        0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
    uint32_t w[64];
    for (int i = 0; i < 16; ++i) {
      w[i] = (uint32_t{p[i * 4]} << 24) | (uint32_t{p[i * 4 + 1]} << 16) |
             (uint32_t{p[i * 4 + 2]} << 8) | uint32_t{p[i * 4 + 3]};
    }
    for (int i = 16; i < 64; ++i) {
      const uint32_t s0 =
          Rotate(w[i - 15], 7) ^ Rotate(w[i - 15], 18) ^ (w[i - 15] >> 3);
      const uint32_t s1 =
          Rotate(w[i - 2], 17) ^ Rotate(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = state_[0], b = state_[1], c = state_[2], d = state_[3],
             e = state_[4], f = state_[5], g = state_[6], h = state_[7];
    for (int i = 0; i < 64; ++i) {
      const uint32_t s1 = Rotate(e, 6) ^ Rotate(e, 11) ^ Rotate(e, 25);
      const uint32_t t1 = h + s1 + ((e & f) ^ (~e & g)) + k[i] + w[i];
      const uint32_t s0 = Rotate(a, 2) ^ Rotate(a, 13) ^ Rotate(a, 22);
      const uint32_t t2 = s0 + ((a & b) ^ (a & c) ^ (b & c));
      h = g;
      g = f;
      f = e;
      e = d + t1;
      d = c;
      c = b;
      b = a;
      a = t1 + t2;
    }
    state_[0] += a;
    state_[1] += b;
    state_[2] += c;
    state_[3] += d;
    state_[4] += e;
    state_[5] += f;
    state_[6] += g;
    state_[7] += h;
  }

  uint32_t state_[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  uint8_t block_[64];
  size_t used_ = 0;
  uint64_t length_ = 0;
};
#endif  // !defined(__APPLE__)

// The lowercase hex SHA-256 of the file at `path`, or "" if it cannot be read
// or `cancel` turns true. `progress` is called with the bytes read so far.
template <typename Progress>
std::string Sha256OfFile(const std::string& path,
                         const std::atomic<bool>& cancel,
                         Progress progress) {
  FILE* file = std::fopen(path.c_str(), "rb");
  if (!file) {
    return "";
  }
#if defined(__APPLE__)
  CC_SHA256_CTX context;
  CC_SHA256_Init(&context);
#else
  Sha256 context;
#endif
  std::vector<uint8_t> buffer(8 << 20);
  uint64_t done = 0;
  size_t got;
  while ((got = std::fread(buffer.data(), 1, buffer.size(), file)) > 0) {
    if (cancel) {
      std::fclose(file);
      return "";
    }
#if defined(__APPLE__)
    CC_SHA256_Update(&context, buffer.data(), static_cast<CC_LONG>(got));
#else
    context.Update(buffer.data(), got);
#endif
    done += got;
    progress(done);
  }
  const bool failed = std::ferror(file);
  std::fclose(file);
  if (failed) {
    return "";
  }
  uint8_t digest[32];
#if defined(__APPLE__)
  CC_SHA256_Final(digest, &context);
#else
  context.Final(digest);
#endif
  static constexpr char kHex[] = "0123456789abcdef";
  std::string hex;
  for (uint8_t byte : digest) {
    hex += kHex[byte >> 4];
    hex += kHex[byte & 15];
  }
  return hex;
}

}  // namespace dual_translate

#endif  // DUAL_TRANSLATE_HOST_SHA256_H_
