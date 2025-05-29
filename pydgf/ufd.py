import datetime
import re
import numpy as np

from .attributes import Attributes

class UFD:
    _words = None
   
    def __init__(self, ufd_words):
        if len(ufd_words) != 18: raise Exception("Unexpected UFD word size!")
        self._words = ufd_words

    @classmethod
    def new(cls): return cls([0]*18)

    def is_deleted(self): return self._words[0] == 0

    def to_bytes(self, byteorder): return bytes().join(i.to_bytes(2, byteorder) for i in self._words)

    # Should only be ALPHANUM and $
    def get_safe_filename(self):
        return (self._words[0].to_bytes(2) + self._words[1].to_bytes(2) + self._words[2].to_bytes(2) + self._words[3].to_bytes(2) + self._words[4].to_bytes(2) + b'.' + self._words[5].to_bytes(2)).replace(b'\0', b'').decode('ascii')
    def set_safe_filename(self, newname):
        parts = newname.upper().split('.')
        x = "".join(re.findall("[A-Z\\$0-9]", parts[0]))
        x = np.frombuffer(x.encode('ascii') + b'\x00'*10, dtype='>u2', count=5).tolist()
        for i in range(5): self._words[i] = x[i]
        if len(parts) > 1:
            x = "".join(re.findall("[A-Z\\$0-9]", parts[1]))
            self._words[5] = np.frombuffer(x.encode('ascii') + b'\x00\x00', dtype='>u2', count=1).tolist()[0]
        else:
            self._words[5] = 0

    def get_file_attributes(self):
        return Attributes(self._words[6])
    def set_file_attributes(self, attr):
        if type(attr) is Attributes: self._words[6] = attr.attr_word
        elif type(attr) is int: self._words[6] = attr
        elif type(attr) is str: self._words[6] = Attributes.from_string(attr).attr_word
        else: raise Exception("Oops")

    def get_link_attributes(self):
        return Attributes(self._words[7])
    def set_link_attributes(self, attr):
        if type(attr) is Attributes: self._words[7] = attr.attr_word
        elif type(attr) is int: self._words[7] = attr
        elif type(attr) is str: self._words[7] = Attributes.from_string(attr).attr_word
        else: raise Exception("Oops")

    def get_logical_block_count(self): return self._words[8]
    def get_bytes_in_last_block(self): return self._words[9]
    def get_total_byte_count(self):
        count = self.get_logical_block_count()*512 + self.get_bytes_in_last_block()
        return count
    def set_total_byte_count(self, count, attr=None):
        if attr is None: attr = self.get_file_attributes()
        if count == 0:
            self._words[8] = self._words[9] = 0
            return
        if type(attr) is str: attr = Attributes.from_string(attr)
        if type(attr) is not Attributes: raise Exception("Need valid attr if count != 0")
        elif attr.is_sequential():
            self._words[8] = count // 510
            self._words[9] = count % 510
            if self._words[9] == 0:
                self._words[8] -= 1
                self._words[9] = 510
        elif attr.is_contiguous() or attr.is_random():
            self._words[8] = count // 512
            self._words[9] = count % 512
            if self._words[9] == 0:
                self._words[8] -= 1
                self._words[9] = 512
        else: raise Exception("Cannot automatically set byte count as we don't understand its attr")

    def get_address(self): return self._words[10]
    def set_address(self, block_id): self._words[10] = block_id

    def get_accessed_datetime(self):
        return datetime.datetime(1967, 12, 31) + datetime.timedelta(days = self._words[11])
    def set_accessed_datetime_from_words(self, date):
        if type(date) is int: self._words[11] = date
        else: raise Exception("Oops")
    def set_accessed_datetime_from_string(self, datetimestr, datetimefmt="%x"):
        if type(datetimestr) is str:
            if len(datetimestr) == 0:
                self._words[11] = 0
                return
            dt = datetime.datetime.strptime(datetimestr, datetimefmt)
            delta = dt - datetime.datetime(1967, 12, 31)
            if delta.days < 0: raise Exception("Date too old")
            self._words[11] = delta.days
        else: raise Exception("Oops")

    def get_modified_datetime(self):
        return datetime.datetime(1967, 12, 31) + datetime.timedelta(days = self._words[12], hours = int(self._words[13] / 256), minutes = self._words[13] % 256)
    def set_modified_datetime_from_words(self, date, time):
        if type(date) is int: self._words[12] = date
        else: raise Exception("Oops")
        if type(time) is int: self._words[13] = time
        else: raise Exception("Oops")
    def set_modified_datetime_from_string(self, datetimestr, datetimefmt="%x %H:%M"):
        if type(datetimestr) is str:
            if len(datetimestr) == 0:
                self._words[12] = self._words[13] = 0
                return
            dt = datetime.datetime.strptime(datetimestr, datetimefmt)
            delta = dt - datetime.datetime(1967, 12, 31)
            if delta.days < 0: raise Exception("Date too old")
            self._words[12] = delta.days
            hours = int(delta.total_seconds() // 3600) % 24
            minutes = int(delta.total_seconds() // 60) % 60
            self._words[13] = (hours << 8) + minutes
        else: raise Exception("Oops")

    def get_uftuc_string(self):
        uftuc = self._words[16]
        out = ''
        # I think this is right
        if uftuc & 0xC000 == 0xC000: out += 'ROPEN'
        elif uftuc & 0xC000 == 0x8000: out += 'EOPEN'
        elif uftuc & 0xC000 == 0x4000: out += 'OPEN'
        else: out += 'CLOSED'
        out += f' {uftuc & 0x3000}'
        return out
    
    def get_dct_link(self):
        return self._words[17]
    def set_dct_link(self, word):
        self._words[17] = word

    def is_file(self): return self.get_file_attributes().is_file()
    def is_dir(self): return self.get_file_attributes().is_dir()
    def is_link(self): return self.get_file_attributes().is_link()
    def is_contiguous(self): return self.get_file_attributes().is_contiguous()
    def is_random(self): return self.get_file_attributes().is_random()
    def is_sequential(self): return self.get_file_attributes().is_sequential()
    def is_permanent(self): return self.get_file_attributes().is_permanent()

    def get_sysdr_fib_offset(self, frame_size):
        # 019-000048-04 (Page 6-6, PDF Page 88)
        offset = 0
        for i in range(6): offset += self._words[i]
        offset &= 0xFFFF
        return offset % frame_size

    def dump(self, indent = 0, frame_size = None, sysdr_fib_offset = None):
        print(f"{'\t'*indent}{self.get_safe_filename()}")
        indent += 1
        print(f"{'\t'*indent}File Attributes: {self.get_file_attributes()} ({self._words[6]})")
        print(f"{'\t'*indent}Link Attributes: {self._words[7]}")
        print(f"{'\t'*indent}Number of logical blocks: {self._words[8]}")
        print(f"{'\t'*indent}Number of bytes in the last block: {self._words[9]}")
        print(f"{'\t'*indent}Address: {self.get_address()}")
        print(f"{'\t'*indent}Last accessed: {self._words[11]} (Days since January 1, 1968)")
        print(f"{'\t'*indent}Last modified: {self._words[12]} (Days since January 1, 1968)")
        print(f"{'\t'*indent}Hour/Minute modified: {int(self._words[13] / 256)} / {self._words[13] % 256}")
        print(f"{'\t'*indent}Temp1: {self._words[14]}")
        print(f"{'\t'*indent}Temp2: {self._words[15]}")
        print(f"{'\t'*indent}UFTUC: {self.get_uftuc_string()} ({self._words[16]})")
        print(f"{'\t'*indent}DCT Link: {self._words[17]}")
        if frame_size is not None and sysdr_fib_offset is not None:
            offset = self.get_sysdr_fib_offset(frame_size)
            valid_offset = sysdr_fib_offset == offset
            if valid_offset: print(f"{'\t'*indent}SYS.DR Offset: VALID ({offset})")
            else: print(f"{'\t'*indent}SYS.DR Offset: INVALID ({sysdr_fib_offset}!={offset})")

