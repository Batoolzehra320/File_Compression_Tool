import os
import heapq
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional
import time

@dataclass
class CompressionResult:
    success: bool
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    processing_time: float = 0.0
    error_message: str = ""
    
    def calculate_savings(self):
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100

@dataclass
class DecompressionResult:
    success: bool
    original_size: int = 0
    decompressed_size: int = 0
    compression_ratio: float = 0.0
    processing_time: float = 0.0
    error_message: str = ""
    
    def calculate_savings(self):
        if self.original_size == 0:
            return 0.0
        return (1 - self.decompressed_size / self.original_size) * 100

class CompressionError(Exception):
    def __init__(self, message="Compression error occurred"):
        self.message = message
        super().__init__(self.message)

class InvalidFormatError(CompressionError):
    def __init__(self, message="Invalid file format"):
        self.message = message
        super().__init__(self.message)

class CorruptedDataError(CompressionError):
    def __init__(self, message="Compressed data is corrupted"):
        self.message = message
        super().__init__(self.message)

class FileNotFoundError(CompressionError):
    def __init__(self, message="File not found"):
        self.message = message
        super().__init__(self.message)

class HuffmanNode:
    def __init__(self, byte_value=None, frequency=0):
        self.byte_value = byte_value  
        self.frequency = frequency
        self.left = None
        self.right = None
    
    def __lt__(self, other):
        return self.frequency < other.frequency
    
    def is_leaf(self):
        return self.left is None and self.right is None

class HuffmanTree:
    def __init__(self, frequency_dict=None):
        if frequency_dict:
            self.root = self._build_tree(frequency_dict)
            self.code_table = {}
            self._generate_codes(self.root, "")
        else:
            self.root = None
            self.code_table = {}
    
    def _build_tree(self, frequency_dict):
        if not frequency_dict:
            raise ValueError("Frequency dictionary cannot be empty")
            
        priority_queue = []
        for byte_val, freq in frequency_dict.items():
            node = HuffmanNode(byte_val, freq)
            heapq.heappush(priority_queue, node)
        
        while len(priority_queue) > 1:
            left = heapq.heappop(priority_queue)
            right = heapq.heappop(priority_queue)
            
            internal_node = HuffmanNode(frequency=left.frequency + right.frequency)
            internal_node.left = left
            internal_node.right = right
            
            heapq.heappush(priority_queue, internal_node)
        
        return priority_queue[0] if priority_queue else None
    
    def _generate_codes(self, node, current_code):
        if node is None:
            return
        
        if node.is_leaf():
            self.code_table[node.byte_value] = current_code
            return
        
        self._generate_codes(node.left, current_code + "0")
        self._generate_codes(node.right, current_code + "1")
    
    def get_code_table(self):
        return self.code_table
    
    def rebuild_tree(self, frequency_dict):
        self.root = self._build_tree(frequency_dict)
        self.code_table = {}
        self._generate_codes(self.root, "")
        return self.root
    
    def decode_data(self, bit_reader, original_size, padding_bits=0):
        if original_size == 0:
            return b""
        
        output_data = bytearray()
        current_node = self.root
        
        if self.root.left is None and self.root.right is None:
            char = self.root.byte_value
            return bytes([char]) * original_size
        
        bits_decoded = 0
        while len(output_data) < original_size:
            bit = bit_reader.read_bit()
            if bit == -1:
                break
            
            if bit == 0:
                current_node = current_node.left
            else:
                current_node = current_node.right
            
            if current_node.byte_value is not None:
                output_data.append(current_node.byte_value)
                current_node = self.root
                bits_decoded += 1
        
        if padding_bits > 0:
            bit_reader.skip_padding(padding_bits)
        
        if len(output_data) != original_size:
            raise CorruptedDataError(
                f"Decompression size mismatch: expected {original_size}, got {len(output_data)}"
            )
        
        return bytes(output_data)

class BitReader:
    def __init__(self, data_bytes):
        self.data = data_bytes
        self.byte_index = 0
        self.bit_index = 0
        self.current_byte = data_bytes[0] if data_bytes else 0
        self.total_bits_read = 0
    
    def read_bit(self):
        if self.byte_index >= len(self.data):
            return -1
        
        bit = (self.current_byte >> (7 - self.bit_index)) & 1
        self.bit_index += 1
        self.total_bits_read += 1
        
        if self.bit_index == 8:
            self.byte_index += 1
            if self.byte_index < len(self.data):
                self.current_byte = self.data[self.byte_index]
            self.bit_index = 0
        
        return bit
    
    def read_bits(self, count):
        result = 0
        for _ in range(count):
            bit = self.read_bit()
            if bit == -1:
                break
            result = (result << 1) | bit
        return result
    
    def skip_padding(self, padding_bits):
        if padding_bits > 0 and self.byte_index < len(self.data):
            self.bit_index += padding_bits
            if self.bit_index >= 8:
                self.byte_index += 1
                self.bit_index = 0

class BitWriter:
    def __init__(self, file_object=None):
        self.file = file_object
        self.current_byte = 0
        self.bit_count = 0
        self.output_buffer = bytearray()
    
    def write_bit(self, bit):
        self.current_byte = (self.current_byte << 1) | (bit & 1)
        self.bit_count += 1
        
        if self.bit_count == 8:
            if self.file:
                self.file.write(bytes([self.current_byte]))
            else:
                self.output_buffer.append(self.current_byte)
            self.current_byte = 0
            self.bit_count = 0
    
    def write_bits(self, bit_string):
        for bit in bit_string:
            self.write_bit(int(bit))
    
    def flush(self):
        padding_bits = 0
        if self.bit_count > 0:
            padding_bits = 8 - self.bit_count
            self.current_byte <<= padding_bits
            if self.file:
                self.file.write(bytes([self.current_byte]))
            else:
                self.output_buffer.append(self.current_byte)
        
        if self.file:
            return padding_bits
        else:
            result = bytes(self.output_buffer)
            self.output_buffer.clear()
            return result, padding_bits

def validate_file_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    if not os.path.isfile(path):
        raise CompressionError(f"Path is not a file: {path}")
    
    if os.path.getsize(path) == 0:
        raise InvalidFormatError("File is empty")

def handle_compression_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CompressionError:
            raise
        except IOError as e:
            raise CompressionError(f"I/O error: {e}")
        except Exception as e:
            raise CompressionError(f"Unexpected error: {e}")
    return wrapper