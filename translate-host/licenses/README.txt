dual-translate-host, the translation program of Dual Page Translate, is part
of Dual (GPL-3.0). It contains:

- llama.cpp and ggml (https://github.com/ggml-org/llama.cpp, release b11846),
  MIT License: llama.cpp-LICENSE.txt
- JSON for Modern C++ by Niels Lohmann (vendored in llama.cpp), MIT License:
  nlohmann-json-LICENSE.txt

The translation model, Gemma 4 E4B (Google DeepMind; 4-bit GGUF by Unsloth),
is not part of Dual. It is downloaded on first use from Hugging Face and is
licensed under the Apache License 2.0:
https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF
