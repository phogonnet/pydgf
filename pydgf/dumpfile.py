import datetime

from .attributes import Attributes
from .ufd import UFD

class Dumpfile:
    def __init__(self, raw_bytes):
        self.raw_bytes = raw_bytes

    def get_files(self, skip_starting_nulls = False):
        offset = 0
        current_ufd = None
        current_data = b''
        current_contiguous_blocks = None

        files = []

        if skip_starting_nulls:
            while self.raw_bytes[offset] == 0:
                offset += 1

        while offset < len(self.raw_bytes):
            block_type = self.raw_bytes[offset]
            offset += 1
            # DOCS: 093-000109-00 (Page B-1, PDF Page 160)
            match block_type:
                case 0xFF: # NAME
                    if current_ufd is not None:
                        files.append((current_ufd, current_data))

                    current_ufd = UFD.new()
                    current_data = b''
                    current_contiguous_blocks = None

                    current_ufd.set_file_attributes(int.from_bytes(self.raw_bytes[offset:offset+2], byteorder="big"))
                    offset += 2

                    if current_ufd.get_file_attributes().is_contiguous() > 0:
                        current_contiguous_blocks = self.raw_bytes[offset:offset+2]
                        offset += 2
                        # FIXME?: WHAT DO WE NEED TO DO WITH THIS INFORMATION?
                    
                    null_terminator = self.raw_bytes.find(b'\0', offset)
                    if null_terminator - offset > 13: raise Exception("Filename is too long!")
                    
                    current_ufd.set_safe_filename(self.raw_bytes[offset:null_terminator].decode('ascii'))
                    offset = null_terminator + 1
                case 0xFE: # DATA
                    length = int.from_bytes(self.raw_bytes[offset:offset+2], byteorder="big")
                    offset += 2
                    
                    # FIXME: Ignoring checksum
                    checksum = self.raw_bytes[offset:offset+2] # wordcount % 2 + total contents?
                    offset += 2

                    if length > 1024:
                        print(f"Length: {length}")
                        raise Exception("Unexpected length!")

                    current_data += self.raw_bytes[offset:offset+length]
                    current_ufd.set_total_byte_count(len(current_data))
                    offset += length
                case 0xFD: # ERROR
                    raise Exception("Unsupported block type: ERROR")
                case 0xFC: # END
                    if current_ufd is not None:
                        files.append((current_ufd, current_data))
                    return files
                case 0xFB: # TIME
                    current_ufd.set_accessed_datetime_from_words(int.from_bytes(self.raw_bytes[offset+0:offset+2], byteorder="big"))
                    current_ufd.set_modified_datetime_from_words(int.from_bytes(self.raw_bytes[offset+2:offset+4], byteorder="big"), int.from_bytes(self.raw_bytes[offset+4:offset+6], byteorder="big"))
                    offset += 6
                case 0xFA: # LINK DATA
                    null_terminator = self.raw_bytes.find(b'\0', offset)
                    if null_terminator - offset > 13: raise Exception("ALT DIR NAME is too long!")
                    alt_dirname = self.raw_bytes[offset:null_terminator].decode('ascii')
                    offset = null_terminator + 1

                    null_terminator = self.raw_bytes.find(b'\0', offset)
                    if null_terminator - offset > 13: raise Exception("LINK ALIAS NAME is too long!")
                    linkname = self.raw_bytes[offset:null_terminator].decode('ascii')
                    offset = null_terminator + 1

                    print(f"WARNING: IGNORING LINK DATA FOR {current_ufd.get_safe_filename()}: {alt_dirname}/{linkname}")
                case 0xF9: # LINK ACCESS ATTRIBUTE
                    current_ufd.set_link_attributes(int.from_bytes(self.raw_bytes[offset:offset+2], byteorder="big"))
                    offset += 2
                case 0xF8: # END OF SEGMENT
                    raise Exception("Unsupported block type: END OF SEGMENT")
                case _:
                    print(f"BLOCK TYPE: {hex(int(block_type))[2:]}")
                    print(f"OFFSET: {offset}")
                    print(f"{self.raw_bytes[offset-10:offset+10]}")
                    raise Exception("Unsupported block type: UNKNOWN/INVALID")
        return files
