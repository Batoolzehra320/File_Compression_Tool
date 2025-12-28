# ZIIPIT - Huffman File Compression Tool

**ZIIPIT** is a Python-based GUI application for compressing and decompressing files using **Huffman coding**. It provides a user-friendly interface for file management, supports user authentication, and maintains a history of all operations.

## Features

- **User Authentication**: Sign up and login functionality.
- **File Compression/Decompression**: Compress files to `.huff` format and decompress them.
- **Progress Tracking**: Real-time progress bar for operations.
- **History Management**: Logs username, file details, operation type, size, and compression ratio.
- **Responsive GUI**: Built with PyQt5, supports dark/light themes.
- **Error Handling**: Displays detailed error messages for failed operations.

## Requirements

- Python 3.x
- PyQt5 (`pip install PyQt5`)
- `compression_api` module (HuffmanCompressionAPI)

## Installation & Running

1. Clone the repository:

```bash
git clone <repo-url>
cd <repo-folder>
