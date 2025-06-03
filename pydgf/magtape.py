# Lots of hard coded things that probably break compatibility with some files, oh well, better then none

# Things like "Free Format" will definitely break things

class Magtape:
    def __init__(self, raw_bytes):
        eof = False
        did_warning = False
        needs_warning = False
        oldrecord = None
        offset = 0
        last_fileno = 0
        self.files = {}
        while offset < len(raw_bytes):
            metadata = raw_bytes[offset:offset+4]
            offset += 4

            # Pretty sure any 9trk files that exist are all in little endian format
            record_length = int.from_bytes(metadata[0:4], byteorder='little')

            if record_length == 0:
                # if verbose: print("Marker")
                if oldrecord == None and not needs_warning:
                    needs_warning = True
                oldrecord = None
                continue
            if record_length == 0xFFFFFFFE:
                # if verbose: print("Erase Gap")
                raise Exception("Unexpected erase gap?")
            if record_length == 0xFFFFFFFF:
                # if verbose: print("End of Medium")
                raise Exception("Unexpected end of medium?")
            if record_length == 0x0000FFFF:
                # "BAD" files
                if verbose: print(f'"BAD" file')
                trail = raw_bytes[offset:offset+4]
                offset += 4
                if len(trail) != 4: raise Exception("Unexpected EOF (Trail)")
                if metadata != trail: raise Exception("Invalid record trail!")        
                continue
            if record_length != 514:
                # Only validated with files that were this way, others do exist though
                print(f"WARNING: WAS EXPECTING RECORD LENGTH OF 514, WAS {record_length}")
                
            record = raw_bytes[offset:offset+record_length]
            offset += record_length
            
            if record_length % 1 != 0: offset += 1 # Padding if length is odd
            
            trail = raw_bytes[offset:offset+4]
            offset += 4

            if len(trail) != 4: raise Exception("Unexpected EOF (Trail)")
            if metadata != trail: raise Exception("Invalid record trail!")

            fileno1 = int.from_bytes(record[record_length-4:record_length-2], byteorder='big')
            fileno2 = int.from_bytes(record[record_length-2:record_length], byteorder='big')
            if fileno1 != fileno2:
                print(f"WARNING: File number does not match! ({fileno1} != {fileno2})")
                #raise Exception("File number does not match!")
            
            if fileno1 > last_fileno + 1 or fileno1 < last_fileno:
                print(f"WARNING: File number sequence is unexpected (last={last_fileno} current={fileno1})")
            last_fileno = fileno1

            if fileno1 > 99:
                # raise Exception("File number is larger then supported by RDOS")
                print(f"WARNING: File number is larger then supported by RDOS ({fileno1})")

            if needs_warning and not did_warning:
                print("WARNING: If any data follows it may have been erased from the tape!")
                did_warning = True
            if not fileno1 in self.files:
                self.files[fileno1] = b""
            self.files[fileno1] += record[0:record_length-4]

            oldrecord = record