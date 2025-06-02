from .ufd import UFD 

class Disk:
    def __init__(self, disk_bytes, byteorder=None):
        def is_byte_order(isbyteorder):
            # Checksum is the first 8 words
            checksum = 0
            for i in range(16):
                word = int.from_bytes(disk_bytes[(3*512)+(i*2)+0:(3*512)+(i*2)+2], isbyteorder)
                checksum += word
            checksum %= 65536
            return checksum == 0
        
        # Attempt to determine byte order if not provided
        if byteorder is None:
            if is_byte_order('big'): byteorder = 'big'
            elif is_byte_order('little'): byteorder = 'little'
            else: raise Exception("Could not determine byteorder automatically, force byteorder to continue")
        
        # Validate byteorder is correct, warn if it doesn't look right
        if not is_byte_order(byteorder): print("WARNING: byteorder looks wrong, decoding may result in invalid data!")
        
        match byteorder:
            case 'little':
                self.disk_bytes = memoryview(bytearray(disk_bytes))
                for i in range(len(disk_bytes)//2):
                    new_value = int.from_bytes(disk_bytes[i*2:(i*2)+2], 'little')
                    self.disk_bytes[i*2:(i*2)+2] = new_value.to_bytes(2, 'big')
            case 'big':
                self.disk_bytes = memoryview(bytearray(disk_bytes))
            case _: raise Exception("HOW!?!?")

    def get_block_words(self, block_id):
        if block_id > len(self.disk_bytes) / 512 or block_id < 0: raise Exception("Tried to access outside the disk!")
        block_words = [0]*256
        for i in range(256):
            block_words[i] = int.from_bytes(self.disk_bytes[(block_id*512)+(i*2):(block_id*512)+(i*2)+2], byteorder='big')
        return block_words
    def get_word(self, block_id, word_offset):
        if block_id > len(self.disk_bytes) / 512 or block_id < 0: raise Exception("Tried to access outside the disk!")
        if word_offset > 256 or word_offset < 0: raise Exception("Offset outside range")
        return int.from_bytes(self.disk_bytes[(block_id*512)+(word_offset*2):(block_id*512)+(word_offset*2)+2], byteorder='big')
    def set_word(self, block_id, word_offset, value):
        if block_id > len(self.disk_bytes) / 512 or block_id < 0: raise Exception("Tried to access outside the disk!")
        if word_offset > 256 or word_offset < 0: raise Exception("Offset outside range")
        if value > 0xFFFF or value < 0: raise Exception("Value outside range")
        self.disk_bytes[(block_id*512)+(word_offset*2):(block_id*512)+(word_offset*2)+2] = value.to_bytes(2, 'big')

    def get_disk_frame_size(self):
        # TODO: Should be able to determine/validate this by looking for SYS.DR loopback at correct hash
        diskinfo_frame_size = self.get_block_words(3)[6]
        other_frame_size = self.get_block_words(7)[17]
        if diskinfo_frame_size != 0:
            if diskinfo_frame_size != other_frame_size:
                print(f"WARNING: dsk frame_size(s) don't match! Using first one {diskinfo_frame_size} != {other_frame_size}")
            return diskinfo_frame_size
        elif other_frame_size != 0:
            print(f"WARNING: dsk info frame_size is zero?!? Returning REV4? backup")
            return other_frame_size
        else:
            print(f"WARNING: dsk frame_size(s) are zero?!?")
            return None
    def set_disk_frame_size(self, frame_size):
        self.set_word(3, 6, frame_size)
        self.set_word(7, 17, frame_size)
        self.fix_diskinfo_checksum()

    def fix_diskinfo_checksum(self):
        checksum = 0
        for i in range(8):
            if i == 1: continue # READ CHECKSUM AS 0
            checksum -= self.get_word(3, i)
        checksum %= 65536
        self.set_word(3, 1, checksum)

    def dump_diskinfo(self, indent = 0):
        print(f"{'\t'*indent}Disk Info:")
        indent += 1
        block_words = self.get_block_words(3)
        match block_words[0]:
            case 0:
                print(f"{'\t'*indent}RevCode: 4.02")
            case 2:
                print(f"{'\t'*indent}RevCode: 5.00")
            case _:
                print(f"{'\t'*indent}RevCode: ?.?? ({block_words[0]})")
                pass

        checksum = 0
        for i in range(8):
            checksum += block_words[i]
        checksum %= 65536
        if checksum == 0:
            print(f"{'\t'*indent}Checksum: VALID ({block_words[1]})")
        else:
            print(f"{'\t'*indent}Checksum: INVALID ({block_words[1]})")

        print(f"{'\t'*indent}Tracks per Cylinder: {block_words[2]}")
        print(f"{'\t'*indent}Sectors per track: {block_words[3]}")
        print(f"{'\t'*indent}Number of Blocks: {block_words[4]*512 + block_words[5]}")
        print(f"{'\t'*indent}Frame Size: {block_words[6]}")
        match block_words[7]:
            case 0x8000:
                print(f"{'\t'*indent}Disk Type Code: 2 WORD ADDRESSES ({block_words[7]})")
            case 0x4000:
                print(f"{'\t'*indent}Disk Type Code: 4234 CONTROLLER ({block_words[7]})")
            case 2:
                print(f"{'\t'*indent}Disk Type Code: 6030 DISKETTE ({block_words[7]})")
            case 1:
                print(f"{'\t'*indent}Disk Type Code: 4231 CONTROLLER ({block_words[7]})")
            case 0:
                print(f"{'\t'*indent}Disk Type Code: ?4048 DRIVE? ({blockWords[7]})")
            case _:
                print(f"{'\t'*indent}Disk Type Code: ? ({block_words[7]})")
    def dump_remap(self, indent = 0):
        print(f"{'\t'*indent}Remap Info:")
        indent += 1
        block_words = self.get_block_words(4)
        print(f"{'\t'*indent}# Valid Words: {block_words[0]}")
        print(f"{'\t'*indent}Start of Remap Area: {block_words[1]*512 + block_words[2]}")
        print(f"{'\t'*indent}Size of Remap Area: {block_words[3]}")
        # TODO: Dump bad block data!
        pass
    def dump_swappointers(self, indent = 0):
        print(f"{'\t'*indent}Swap Pointers:")
        indent += 1
        block_words = self.get_block_words(7)
        print(f"{'\t'*indent}BG1 FileIndexBlock Address: {block_words[1]*512 + block_words[2]}")
        print(f"{'\t'*indent}BG2 FileIndexBlock Address: {block_words[3]*512 + block_words[4]}")
        print(f"{'\t'*indent}BG3 FileIndexBlock Address: {block_words[5]*512 + block_words[6]}")
        print(f"{'\t'*indent}BG4 FileIndexBlock Address: {block_words[7]*512 + block_words[8]}")
        print(f"{'\t'*indent}FG1 FileIndexBlock Address: {block_words[9]*512 + block_words[10]}")
        print(f"{'\t'*indent}FG2 FileIndexBlock Address: {block_words[11]*512 + block_words[12]}")
        print(f"{'\t'*indent}FG3 FileIndexBlock Address: {block_words[13]*512 + block_words[14]}")
        print(f"{'\t'*indent}FG4 FileIndexBlock Address: {block_words[15]*512 + block_words[16]}")
        print(f"{'\t'*indent}Frame Size: {block_words[17]}")
        print(f"{'\t'*indent}Number of overlays: {block_words[18]}")
    def dump_MAPDR(self, indent = 0):
        print(f"{'\t'*indent}MAP.DR:")
        indent += 1
        # Bitmap starts at SYS.DR (Block 6) not at the beginning of the drive!
        print(f"{'\t'*indent}This file is a bitmap of disk blocks in use")
        block_words = self.get_block_words(15)
        print(f"{'\t'*indent}{block_words[0]:>02X} {block_words[1]:>02X} {block_words[2]:>02X}")
    def dump_root_SYSDR(self, indent=0):
        self.dump_directory(6, indent)
    def dump_directory(self, address, indent=0):
        frame_size = self.get_disk_frame_size()
        block_words = self.get_block_words(address)
        # FIXME: This isn't quite right for decoding, its 255 with a link
        for i in range(255):
            if block_words[i] > 0:
                deb = self.get_block_words(block_words[i])
                entries = deb[0]
                if entries > 14:
                    print(f"address: {address}")
                    print(f"frame_size: {frame_size}")
                    print(f"i: {i}")
                    print(f"block_words[i]: {block_words[i]}")
                    print(f"deb: {deb}")
                    print(f"entries: {entries}")
                    print(f"? {self.get_word(block_words[i], 0)}")
                    raise Exception("Unexpected number of entries")
                for e in range(entries):
                    ufd_start = (e*18)+1
                    ufd_end = ((e+1)*18)+1
                    ufd = UFD(deb[ufd_start:ufd_end])
                    
                    if ufd.is_deleted():
                        # print(f"{'\t'*indent}*** FILE IS DELETED: {ufd.getSafeFilename()}")
                        continue

                    ufd.dump(indent, frame_size, i)

                    if ufd.is_dir() and ufd.get_address() != address:
                        self.dump_directory(ufd.get_address(), indent=indent+1)

    def get_file_bytes(self, ufd):
        # DOES NOT SUPPORT 2WORD DRIVES
        # WHAT HAPPENS IF get_bytes_in_last_block returns an odd number?

        address = ufd.get_address()
        if address < 16: return # THIS WOULD MEAN IT'S A "SYSTEM" area and shouldn't get read here (ex: MAP.DR)
        attr = ufd.get_file_attributes()
        data = b''

        if attr.is_dir():
            # Directory, just skip the data
            return
        elif attr.is_link():
            # LINK, don't bother following to get data
            return
        elif attr.is_random():
            part = 0
            count = ufd.get_logical_block_count()
            if count > 510:
                # FIXME: Need to support reading the last word so we get the next FIB
                raise Exception("UNSUPPORTED LARGE RANDOM FILE")
            while part <= count:
                part_address = int.from_bytes(self.disk_bytes[(address*512)+(part*2):(address*512)+(part*2)+2], byteorder='big')
                if part == count:
                    data += self.disk_bytes[part_address*512:(part_address*512)+ufd.get_bytes_in_last_block()]
                else:
                    data += self.disk_bytes[part_address*512:(part_address*512)+512]
                part += 1
            return data
        elif attr.is_contiguous():
            # CONTIGUOUS FILE
            count = ufd.get_logical_block_count()
            # print(f"{ufd.get_safe_filename()}: {ufd.get_file_attribute_string()} {ufd.get_address()} {count} {ufd.get_total_byte_count()}")
            for i in range(count+1):
                if i == count: data += self.disk_bytes[(address+i)*512:((address+i)*512)+ufd.get_bytes_in_last_block()]
                else: data += self.disk_bytes[(address+i)*512:((address+i)*512)+512]
            return data
        elif attr.is_sequential():
            # SEQ FILE IF NOT CONT/RANDOM
            try:
                count = ufd.get_logical_block_count()
                previous_address = 0
                for i in range(count+1):
                    if i == count:
                        data += self.disk_bytes[address*512:(address*512)+ufd.get_bytes_in_last_block()]
                    else:
                        data += self.disk_bytes[address*512:(address*512)+510]
                    next_address = int.from_bytes(self.disk_bytes[(address*512)+510:(address*512)+512], byteorder='big')
                    temp = address
                    address = previous_address ^ next_address # YES REALLY
                    previous_address = temp
                return data
            finally:
                return data

    def set_map_block_bit(self, block_id):
        print(f"set_map_block_bit({block_id})")
        word = (block_id - 6) // 16
        bit = 15 - ((block_id - 6) % 16)
        map_block = 15 + (word // 256)
        map_word = word % 256
        self.set_word(map_block, map_word, self.get_word(map_block, map_word) | (1<<bit))
    def get_map_block_word(self, block_id):
        word = (block_id - 6) // 16
        map_block = 15 + (word // 256)
        map_word = word % 256
        return self.get_word(map_block, map_word)
    def get_map_block_bit(self, block_id):
        word = (block_id - 6) // 16
        map_block = 15 + (word // 256)
        map_word = word % 256
        bit = 15 - ((block_id - 6) % 16)
        return (self.get_word(map_block, map_word) & (1<<bit)) == 0
    def allocate_blocks(self, count):
        start_block = 16
        end_of_disk = self.get_word(3, 5)

        while start_block < end_of_disk:
            # Fast path full words
            if self.get_map_block_word(start_block) == 0xFFFF:
                start_block = (((start_block + 10) // 16) * 16) + 6
                continue
            range_start = start_block
            for bc in range(count):
                if self.get_map_block_bit(start_block) == False: break
                start_block += 1
            if range_start + count == start_block:
                for i in range(count): self.set_map_block_bit(range_start + i)
                return range_start
            start_block += 1
        raise Exception("OUT OF SPACE")

    def add_frames_to_sysdr_block(self, sysdr_block_id):
        frame_size = self.get_disk_frame_size()
        # Find next empty frames area
        empty_entry_block = sysdr_block_id
        empty_entry_index = 0
        while self.get_word(empty_entry_block, empty_entry_index) != 0:
            empty_entry_index += 1
            if empty_entry_index >= (255-frame_size): raise Exception("We don't support HUGE directories at this time")
        new_blocks_index = self.allocate_blocks(frame_size)
        for i in range(frame_size):
            self.set_word(empty_entry_block, empty_entry_index + i, new_blocks_index + i)
        if empty_entry_index == 0:
            # ADD SYS.DR loopback
            ufd = UFD.new()
            ufd.set_safe_filename("SYS.DR")
            ufd.set_file_attributes("AYDPW")
            ufd.set_address(sysdr_block_id)
            ufd.set_dct_link(0o33) # FORCED TO DEV_DISK
            # FIXME: FAKE UFD DATASIZE
            ufd.set_total_byte_count(512*self.get_disk_frame_size())
            self.add_ufd(sysdr_block_id, ufd)
        
            # ADD MAP.DR loopback
            ufd = UFD.new()
            ufd.set_safe_filename("MAP.DR")
            ufd.set_file_attributes("ACPW")
            ufd.set_address(15) # ufd.set_address(map_block_id)
            ufd.set_dct_link(0o33) # FORCED TO DEV_DISK
            #       Map starts at block 6
            ufd.set_total_byte_count(((len(self.disk_bytes)//512) - 6)//8, 'C')
            self.add_ufd(sysdr_block_id, ufd)
        else:
            # FIXME: Update SYS.DR Size?
            raise Exception("FIXME")

    def add_file(self, sysdr_block_id, ufd, data):
        # if not attr.is_dir() and ufd.get_total_byte_count() != len(data): raise Exception("UFD datasize didn't match data")

        # FORCE TO DEV_DISK IF 0 OTHERWISE FILE WILL NOT EXIST
        if ufd.get_dct_link() == 0: ufd.set_dct_link(0o33)

        # Add file (Update UFD Address as well)
        if ufd.is_dir():
            if not ufd.is_random(): raise Exception('Expected directory to be ATTR "RANDOM" as that is how they are')
            ufd.set_address(self.allocate_blocks(1))
            ufd.set_total_byte_count(self.get_disk_frame_size() * 512)
            self.add_frames_to_sysdr_block(ufd.get_address())
            self.add_ufd(sysdr_block_id, ufd)
            return ufd.get_address()
        elif data is None or len(data) == 0:
            ufd.set_address(self.allocate_blocks(1))
        elif ufd.is_contiguous():
            bytes_left = len(data)
            data_index = 0
            while bytes_left > 0:
                dsk_offset = None
                if bytes_left == len(data):
                    ufd.set_address(self.allocate_blocks(1))
                    dsk_offset = ufd.get_address() * 512
                else:
                    dsk_offset = self.allocate_blocks(1) * 512
                if bytes_left >= 512:
                    self.disk_bytes[dsk_offset:dsk_offset+512] = data[(data_index*512):(data_index*512)+512]
                else:
                    self.disk_bytes[dsk_offset:dsk_offset+bytes_left] = data[(data_index*512):(data_index*512)+bytes_left]
                data_index += 1
                bytes_left -= 512
        elif ufd.is_sequential():
            bytes_left = len(data)
            data_index = 0
            prev_block = 0
            next_block = self.allocate_blocks(1)
            ufd.set_address(next_block)
            while next_block != 0:
                dsk_offset = next_block * 512
                if bytes_left >= 510:
                    self.disk_bytes[dsk_offset:dsk_offset+510] = data[data_index*510:(data_index*510)+510]
                    next_block = self.allocate_blocks(1)
                else:
                    self.disk_bytes[dsk_offset:dsk_offset+bytes_left] = data[data_index*510:(data_index*510)+bytes_left]
                    next_block = 0
                link = prev_block ^ next_block
                self.disk_bytes[dsk_offset+510:dsk_offset+512] = link.to_bytes(2, 'big')
                data_index += 1
                bytes_left -= 510
        elif ufd.is_random():
            rnd_block = self.allocate_blocks(1)
            rnd_index = 0
            bytes_left = len(data)
            data_index = 0
            ufd.set_address(rnd_block)
            while bytes_left > 0:
                data_block = self.allocate_blocks(1)
                # Write RandomDataBlockLink
                self.set_word(rnd_block, rnd_index, data_block)
                rnd_index += 1
                if rnd_index >= 255: raise Exception("Currently don't support 'RANDOM' files this large")
                # Write Data
                if bytes_left >= 512:
                    self.disk_bytes[data_block*512:(data_block*512)+512] = data[(data_index*512):(data_index*512)+512]
                else:
                    self.disk_bytes[data_block*512:(data_block*512)+bytes_left] = data[(data_index*512):(data_index*512)+bytes_left]
                data_index += 1
                bytes_left -= 512
        else: raise Exception("WHAT HAPPENED?!?!")
        
        self.add_ufd(sysdr_block_id, ufd)

    # Used by this class only
    def add_ufd(self, sysdr_block_id, ufd):
        # Add UFD to SYSDR
        fib_index = ufd.get_sysdr_fib_offset(self.get_disk_frame_size())
        fib_block = None
        fib_block_entry_index = None
        while fib_block_entry_index is None:
            fib_block = self.get_word(sysdr_block_id, fib_index)
            for entry_index in range(14):
                testufd = UFD(self.get_block_words(fib_block)[(entry_index*18)+1:(entry_index*18)+19])
                if not testufd.is_deleted(): continue
                fib_block_entry_index = entry_index
                break
            if fib_block_entry_index is None:
                fib_index += self.get_disk_frame_size()
                if fib_index > 255:
                    # FIXME: Support adding extra frames
                    raise Exception("Currently don't support this action at this time")
        self.disk_bytes[(fib_block*512)+(fib_block_entry_index*36)+2:(fib_block*512)+(fib_block_entry_index*36)+38] = ufd.to_bytes('big')
        # Inc File Count
        self.set_word(fib_block, 0, self.get_word(fib_block, 0) + 1)
        # Update max ever count if needed
        if self.get_word(fib_block, 254) < self.get_word(fib_block, 0):
            self.set_word(fib_block, 254, self.get_word(fib_block, 0))