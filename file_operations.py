import os
import struct
import time
from typing import Dict, Tuple
from huffman_core import (
    HuffmanTree, BitReader, BitWriter, CompressionResult, 
    DecompressionResult, CompressionError, InvalidFormatError, 
    CorruptedDataError, FileNotFoundError, validate_file_path,
    handle_compression_errors
)

class FileCompressor:
    def __init__(self):
        self.magic_number = b'HUFF'
    
    @handle_compression_errors
    def compress_file(self, input_path: str, output_path: str) -> CompressionResult:
        validate_file_path(input_path)
        
        start_time = time.time()
        
        with open(input_path, 'rb') as f:
            original_data = f.read()
        
        if not original_data:
            raise CompressionError("Input file is empty")
        
        original_size = len(original_data)
        
        frequency_dict = self._calculate_frequency(original_data)
        unique_byte_count = len(frequency_dict)
        huffman_tree = HuffmanTree(frequency_dict)
        code_table = huffman_tree.get_code_table()
        
        with open(output_path, 'wb') as f:
            header_position = self._write_file_header(f, original_size, unique_byte_count, frequency_dict)
            
            bit_writer = BitWriter(f)
            for byte_val in original_data:
                code = code_table[byte_val]
                bit_writer.write_bits(code)
            padding_bits = bit_writer.flush()
            
            self._update_padding_info(output_path, header_position, padding_bits, unique_byte_count)
        
        compressed_size = os.path.getsize(output_path)
        processing_time = time.time() - start_time
        
        return CompressionResult(
            success=True,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size,
            processing_time=processing_time
        )
    
    @handle_compression_errors
    def decompress_file(self, input_path: str, output_path: str) -> DecompressionResult:
        validate_file_path(input_path)
        
        start_time = time.time()
        
        with open(input_path, 'rb') as infile:
            original_size, frequency_dict, padding_bits = self._read_file_header(infile)
            
            compressed_data = infile.read()
            
            huffman_tree = HuffmanTree()
            huffman_tree.rebuild_tree(frequency_dict)
            
            bit_reader = BitReader(compressed_data)
            decompressed_data = huffman_tree.decode_data(bit_reader, original_size, padding_bits)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(decompressed_data)
        
        processing_time = time.time() - start_time
        
        return DecompressionResult(
            success=True,
            original_size=original_size,
            decompressed_size=len(decompressed_data),
            compression_ratio=len(decompressed_data) / original_size if original_size > 0 else 0,
            processing_time=processing_time
        )
    
    def _calculate_frequency(self, data: bytes) -> Dict[int, int]:
        frequency_dict = {}
        for byte_val in data:
            frequency_dict[byte_val] = frequency_dict.get(byte_val, 0) + 1
        return frequency_dict
    
    def _write_file_header(self, file_obj, original_size: int, unique_count: int, 
                          frequency_dict: Dict[int, int]) -> int:
        position = file_obj.tell()
        
        file_obj.write(self.magic_number)
        file_obj.write(struct.pack('>I', original_size))
        file_obj.write(struct.pack('B', unique_count))
        
        for byte_val, freq in frequency_dict.items():
            file_obj.write(struct.pack('B', byte_val))
            file_obj.write(struct.pack('>I', freq))
        
        file_obj.write(struct.pack('B', 0))
        
        return position
    
    def _read_file_header(self, file_obj) -> Tuple[int, Dict[int, int], int]:
        magic = file_obj.read(4)
        if magic != self.magic_number:
            raise InvalidFormatError("Not a valid Huffman compressed file")
        
        original_size_bytes = file_obj.read(4)
        if len(original_size_bytes) < 4:
            raise CorruptedDataError("Incomplete header: missing file size")
        original_size = struct.unpack('>I', original_size_bytes)[0]
        
        unique_count_bytes = file_obj.read(1)
        if len(unique_count_bytes) < 1:
            raise CorruptedDataError("Incomplete header: missing unique count")
        unique_count = struct.unpack('B', unique_count_bytes)[0]
        
        frequency_dict = {}
        for _ in range(unique_count):
            char_byte = file_obj.read(1)
            freq_bytes = file_obj.read(4)
            
            if len(char_byte) < 1 or len(freq_bytes) < 4:
                raise CorruptedDataError("Incomplete frequency table")
            
            char_val = struct.unpack('B', char_byte)[0]
            frequency = struct.unpack('>I', freq_bytes)[0]
            frequency_dict[char_val] = frequency
        
        padding_bytes = file_obj.read(1)
        if len(padding_bytes) < 1:
            raise CorruptedDataError("Incomplete header: missing padding info")
        padding_bits = struct.unpack('B', padding_bytes)[0]
        
        return original_size, frequency_dict, padding_bits
    
    def _update_padding_info(self, file_path: str, header_position: int, 
                           padding_bits: int, unique_count: int):
        with open(file_path, 'r+b') as f:
            padding_position = header_position + 4 + 4 + 1 + (unique_count * 5)
            f.seek(padding_position)
            f.write(struct.pack('B', padding_bits))
    
    def get_file_info(self, file_path: str):
        try:
            validate_file_path(file_path)
            
            with open(file_path, 'rb') as f:
                original_size, frequency_dict, padding_bits = self._read_file_header(f)
            
            return {
                'is_compressed': True,
                'file_type': 'compressed_file',
                'original_size': original_size,
                'unique_bytes': len(frequency_dict),
                'can_decompress': True,
                'compression_method': 'Huffman Coding'
            }
        except CompressionError as e:
            return {
                'is_compressed': False,
                'file_type': 'unknown',
                'original_size': 0,
                'unique_bytes': 0,
                'can_decompress': False,
                'error_message': str(e)
            }