import os
from typing import Optional
from huffman_core import (
    CompressionResult, DecompressionResult, CompressionError,
    InvalidFormatError, CorruptedDataError, FileNotFoundError,
    validate_file_path, handle_compression_errors
)
from file_operations import FileCompressor

class HuffmanCompressionAPI:
    def __init__(self):
        self.file_compressor = FileCompressor()
    
    @handle_compression_errors
    def compress(self, input_path: str, output_path: str, 
                progress_callback: Optional[callable] = None) -> CompressionResult:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path not found: {input_path}")
        
        if progress_callback:
            progress_callback(0, 100, "starting", "Starting compression")
        
        if os.path.isfile(input_path):
            if progress_callback:
                progress_callback(0, 100, "compressing", os.path.basename(input_path))
            return self.file_compressor.compress_file(input_path, output_path)
        else:
            raise CompressionError(f"Invalid input path: {input_path}")
    
    @handle_compression_errors
    def decompress(self, input_path: str, output_path: str,
                  progress_callback: Optional[callable] = None) -> DecompressionResult:
        validate_file_path(input_path)
        
        if progress_callback:
            progress_callback(0, 100, "starting", "Starting decompression")
        
        file_type = self._detect_file_type(input_path)

        if progress_callback:
            progress_callback(0, 100, "decompressing", os.path.basename(input_path))
        
        if file_type == "compressed_file":
            return self.file_compressor.decompress_file(input_path, output_path)
        else:
            raise InvalidFormatError(f"Unsupported file format: {input_path}")
    
    def get_file_info(self, file_path: str) -> dict:
        try:
            validate_file_path(file_path)
            
            file_type = self._detect_file_type(file_path)
            
            if file_type == "compressed_file":
                return self.file_compressor.get_file_info(file_path)
            else:
                file_size = os.path.getsize(file_path)
                return {
                    'is_compressed': False,
                    'file_type': 'regular_file',
                    'original_size': file_size,
                    'compressed_size': file_size,
                    'can_compress': True,
                    'compression_method': 'Huffman Coding'
                }
                
        except CompressionError as e:
            return {
                'is_compressed': False,
                'file_type': 'unknown',
                'original_size': 0,
                'compressed_size': 0,
                'can_compress': False,
                'can_decompress': False,
                'error_message': str(e)
            }
    
    def _detect_file_type(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(4)
                if magic == b'HUFF':
                    return "compressed_file"
                return "unknown"
        except Exception:
            return "unknown"
    
    def get_supported_formats(self) -> dict:
        return {
            'compression_methods': ['Huffman Coding'],
            'supported_inputs': {
                'single_files': 'All file types'
            },
            'file_extensions': ['.huff'],
            'features': [
                'Lossless compression',
                'Progress tracking',
                'Error recovery'
            ]
        }

def compress_file(input_path: str, output_path: str = None) -> CompressionResult:
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = base_name + '.huff'
    
    api = HuffmanCompressionAPI()
    return api.compress(input_path, output_path)

def decompress_file(input_path: str, output_path: str = None) -> DecompressionResult:
    if output_path is None:
        base_name = os.path.splitext(input_path)[0]
        output_path = base_name + '_decompressed' + os.path.splitext(input_path)[1]
    
    api = HuffmanCompressionAPI()
    return api.decompress(input_path, output_path)