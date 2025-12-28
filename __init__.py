from .huffman_core import (
    HuffmanNode, HuffmanTree, BitReader, BitWriter,
    CompressionResult, DecompressionResult,
    CompressionError, InvalidFormatError, CorruptedDataError, 
    FileNotFoundError,
    validate_file_path, handle_compression_errors
)

from .file_operations import FileCompressor
from .compression_api import HuffmanCompressionAPI, compress_file, decompress_file

__version__ = "1.0.0"
__author__ = "Compression Tool Team"
__description__ = "Huffman coding compression for individual files"

__all__ = [
    'HuffmanNode', 'HuffmanTree', 'BitReader', 'BitWriter',
    'CompressionResult', 'DecompressionResult',
    'CompressionError', 'InvalidFormatError', 'CorruptedDataError',
    'FileNotFoundError',
    'validate_file_path', 'handle_compression_errors',
    'FileCompressor',
    'HuffmanCompressionAPI',
    'compress_file', 'decompress_file'
]

def get_version():
    return __version__

def get_supported_features():
    api = HuffmanCompressionAPI()
    return api.get_supported_formats()