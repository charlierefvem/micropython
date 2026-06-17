from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

KNOWN_TAGS = {
    "type",
    "range",
    "units",
    "alias",
    "count",
    "labels",
    "block_size_bytes",
    "alignment_bytes",
    "description",
    "size_bytes",
    "extends_to_end_of_block",
}

SPACER = "  "
PATH_SEPARATOR = " \N{RIGHTWARDS ARROW} "

SIZE_FROM_TYPE = {
    "FLOAT32": 4,
    "FLOAT64": 8,
    "INT8":    1,
    "INT16":   2,
    "INT32":   4,
    "INT64":   8, 
    "UINT8":   1,
    "UINT16":  2,
    "UINT32":  4,
    "UINT64":  8,
}

def pascal_case_to_prefix(text: str) -> str:
    '''
    Extracts uppercase letters from a PascalCase string.
    '''
    return "".join([char for char in text if char.isupper()])

@dataclass
class Node:
    '''
    A generic node in the abstract tree representation of the register map.
    This class is meant to be a base class and inherited from by specific node
    classes.
    '''
    Name: str
    Path: tuple[str, ...]
    
    def full_name(self):
        '''
        Construct a full name using the path of a node as a prefix
        '''
        return ".".join(self.Path)
        
    
    def const_name(self, suffix):
        '''
        Construct a name for a constant using the path of a node as a prefix
        '''
        return "_".join(part.upper() for part in self.Path) + "_" + suffix
    
    def retrieve(self, name):
        '''
        Retrieve a node by name by recusively scanning nodes until a hit is
        found
        '''
        
        # If this node is a Tag, return its value immediately if a hit is found
        if isinstance(self, Tag):
            if self.Name == name:
                return self.Value
            
        # If this node is a Map, return its value if a hit is found or recurse
        elif isinstance(self, Map):
            if self.Name == name:
                return self
            else:
                for system in self.Systems:
                    ret = system.retrieve(name)
                    if ret is not None:
                        return ret
                    
        # If this node is a Group return its value if a hit is found or recurse
        elif isinstance(self, Group):
            if self.Name == name:
                return self
            else:
                for group in self.Groups:
                    ret = group.retrieve(name)
                    if ret is not None:
                        return ret
        
        # If this node is a Register, return its value if a hit is found
        elif isinstance(self, Register):
            if self.Name == name:
                return self
        
        # If no hit was found and no recursion is needed then we need to back
        # out gracefully and resume searching order nodes
        return None

@dataclass
class Tag(Node):
    '''
    A node in the abstract tree representation of the register map representing
    a tag, which is how metadata about the map and registerd is stored. 
    '''
    Value: float | int | str | bool | list[float | int]
    
    def __repr__(self) -> str:
        '''
        String representation of a Tag node
        '''
        
        # Since a tag can be a str or numeric we format its string
        # representation with or without quotation marks
        if isinstance(self.Value, str):
            return f"{self.Name} = '{self.Value}'"
        else:
            return f"{self.Name} = {self.Value}"
    
    def unroll(self, kind=None):
        '''
        Unroll a Tag node
        '''
        
        # Default to searching for Register
        if kind is None:
            kind = Register
        
        # For a Tag there are no children so we don't need to recurse
        flat_list = []
        if kind is Tag:
            flat_list.append(self)
        
        return flat_list
    
    
@dataclass
class Register(Node):
    '''
    A node in the abstract tree representation of the register map representing
    a single register. 
    '''
    Tags:   dict[str, Tag]
    Alias:  str | None = field(default=None, init=False)
    Type:   str | None = field(default=None, init=False)
    Units:  str | None = field(default=None, init=False)
    Size:   int | None = field(default=None, init=False)
    Offset: int | None = field(default=None, init=False)
    
    def __repr__(self) -> str:
        '''
        String representation of a Register node
        '''
        lines = []
        lines.append(f"{self.Name}")
        lines.append(SPACER + "Path = " + PATH_SEPARATOR.join(self.Path))
        
        for tag in self.Tags.values():
            tag_lines = str(tag)
            for line in tag_lines.strip("\r\n").split("\r\n"):
                lines.append(SPACER + line)
            
        return "\r\n".join(lines)

    def unroll(self, kind=None):
        '''
        Unroll a Register node
        '''
        
        # Default to searching for registers
        if kind is None:
            kind = Register
        
        flat_list = []
        
        # If hit, append Register
        if kind is Register:
            # Looking for a Register
            flat_list.append(self)
        # Otherwise, recurse through this node's Tags
        for tag in self.Tags.values():
            flat_list.extend(tag.unroll(kind))
        
        return flat_list
    
    def tags_to_attributes(self):
        '''
        Converts any existing tags into class atrributes.
        '''
        if "alias" in self.Tags:
            self.Alias = self.Tags["alias"].Value
        if "type" in self.Tags:
            self.Type = self.Tags["type"].Value
        if "units" in self.Tags:
             self.Units = self.Tags["units"].Value
    
    def calc_size(self):
        self.Size = SIZE_FROM_TYPE[self.Type]
        print(SPACER*2 + f"{self.full_name()} is {self.Size} bytes")

    def calc_offset(self, next_offset, word_size=1, align=False):
        self.Offset = next_offset
        next_offset += self.Size
        # Check for boundary alignment
        if align and next_offset % word_size != 0:
            next_offset = (next_offset // word_size + 1) * word_size
            print(SPACER*1 + f"{self.full_name()} padded from"
                  f" {SIZE_FROM_TYPE[self.Type]} to"
                  f" {next_offset-self.Offset} bytes for word alignment")
        print(SPACER*2 + f"{self.full_name()} is {self.Offset} bytes offset from base")
        return next_offset
    
@dataclass
class Group(Node):
    '''
    A node in the abstract tree representation of the register map representing
    a group of registers and tags.
    '''
    Tags:          dict[str, Tag]
    Groups:        list[Register | Group]
    Alias:         str | None = field(default=None, init=False)
    Type:          str | None = field(default=None, init=False)
    UsedSize:      int | None = field(default=None, init=False)
    AllocatedSize: int | None = field(default=None, init=False)
    Offset:        int | None = field(default=None, init=False)
    
    def __repr__(self) -> str:
        '''
        String representation of a Group node
        '''
        lines = []
        lines.append(f"{self.Name}")
        lines.append(SPACER + "Path = " + PATH_SEPARATOR.join(self.Path))
        
        for tag in self.Tags.values():
            tag_lines = str(tag)
            for line in tag_lines.strip("\r\n").split("\r\n"):
                lines.append(SPACER + line)
                
        for group in self.Groups:
            group_lines = str(group)
            for line in group_lines.strip("\r\n").split("\r\n"):
                lines.append(SPACER + line)
                
        return "\r\n".join(lines)
    
    def unroll(self, kind=None):
        '''
        Unroll a Group node
        '''
        
        # Default to searching for registers
        if kind is None:
            kind = Register
        
        flat_list = []
        
        # If hit append Group
        if kind is Group:
            flat_list.append(self)
        
        # Recurse through this groups Tags
        for tag in self.Tags.values():
            flat_list.extend(tag.unroll(kind))
        # Recurse through subgroups
        for group in self.Groups:
            flat_list.extend(group.unroll(kind))
        
        return flat_list
    
    def tags_to_attributes(self):
        '''
        Converts any existing tags into class atrributes.
        '''
        if "alias" in self.Tags:
            self.Alias = self.Tags["alias"].Value
        if "type" in self.Tags:
            self.Type = self.Tags["type"].Value
            
    def calc_size(self, word_size=1, align=False, block_size=None):
        # First register in the group needs to already have an offset but
        # the first register may be hiding in a subgroup
        start = None
        end = None
        end_size = None
        regs = self.unroll(Register)
        if len(regs):
            for reg in regs:
                start = reg.Offset
                if start is not None:
                    break
                
            for reg in reversed(regs):
                end = reg.Offset
                end_size = reg.Size
                if end is not None:
                    break

            self.UsedSize = end - start + end_size
            if align and self.UsedSize % word_size != 0:
                self.AllocatedSize = (self.UsedSize // word_size + 1) * word_size
            elif block_size :
                self.AllocatedSize = block_size
            else:
                self.AllocatedSize = self.UsedSize
            print(SPACER*2 + f"{self.full_name()} is {self.UsedSize} bytes")
            print(SPACER*2 + f"{self.full_name()} allocates {self.AllocatedSize} bytes")
 
    def calc_offset(self, word_size=1, align=False):
        regs = self.unroll(Register)
        if len(regs):
            self.Offset = regs[0].Offset
            print(SPACER*2 + f"{self.full_name()} is {self.Offset} bytes offset from base")
 
@dataclass
class Map(Node):
    '''
    The root node in the abstract tree representation of the register map.
    '''
    Systems:   list[Register | Group]
    Metadata:  Group
    WordSize:  int | None = field(default=None, init=False)
    BlockSize: int | None = field(default=None, init=False)
    TotalSize: int | None = field(default=None, init=False)
    Align :    bool| None = field(default=None, init=False)
    Extend:    bool| None = field(default=None, init=False)
    
    def __repr__(self) -> str:
        '''
        String representation of a Map (root) node
        '''
        lines = []
        lines.append(f"{self.Name}")
        
        for system in self.Systems:
            sys_lines = str(system)
            for line in sys_lines.strip("\r\n").split("\r\n"):
                lines.append(SPACER + line)
                
        return "\r\n".join(lines)

    def unroll(self, kind=None):
        '''
        Unroll a Map node
        '''
        
        # Default to searching for registers
        if kind is None:
            kind = Register
        
        flat_list = []
        
        # If hit, append Map
        if kind is Map:
            flat_list.append(self)
            
        # Check subsystems
        for system in self.Systems:
            flat_list.extend(system.unroll(kind))
        
        return flat_list
    
    def calc_size(self):
        self.TotalSize = sum(sys.AllocatedSize for sys in self.Systems)

def walk(name, value, parent_path = ()):
    '''
    Traverses a node or subnode. Should be applied to each {name:value} pair in
    the dict represenation of the JSON file describing the register map
    '''

    # Compute a new path from the parent path
    path = parent_path + (name,)
    
    # If the item is a tag, return it immediately
    if not isinstance(value, dict):
        return Tag(name, path, value)
    
    # Otherwise, keep traversing building tags and children
    tags = dict()
    children = []
    for key, item in value.items():
        # Get a child and use it to decode tag vs not tag
        child = walk(key, item, path)
        # Append children that are tags to this group or register
        if isinstance(child, Tag):
            tags[child.Name] = child
        # Groups require recursion to get all subgroups and tags
        else:
            children.append(child)
            
    # After traversing return a register or a group
    if "type" in value:
        return Register(name, path, tags)
    else:
        return Group(name, path, tags, children)

def build_map(filename="register_definitions.json",
              output_filename="register_interface.py",
              use_literals = True,
              use_substructs = False,
              private_dicts = True):
    '''
    Build a fully featured Python object representing the register map. The
    produced Map object contains all registers and tags. The object is parsed
    in multiple passes
    0) Process metadata for register map
    1) Promote tags to class attributes
    2) Determine sizes and offsets for each register, group, system, and the 
       map as a whole
    3) Generate constant definitions for register sizes and offsets
    4) Generate micropython compatible class definitions for a firmware-ready
       register map implementation using nparray and uctypes.struct objects.
    '''

    # Open the file, read it, and convert from JSON to a nested dictionary
    with open(filename) as infile:
        schema = json.load(infile)

    print(f"Loaded file {filename}")
    print("")
    
    
    # Pass 0 - generate the map in the first place
    # For each child of the system do a full depth set of walks to grab
    # grandchildren, etc. Use the results to build a Map object
    metadata = walk("Metadata", schema["Metadata"])
    systems = [walk(name, value) for name, value in schema["Systems"].items()]
    regs = Map("RegisterMap", (), systems, metadata)
    

    # Check memory layout for the register map to find
    #  word size    Word size for alignment
    #  block size   Block size for extension
    #  align flag   Defines whether word boundaries are enforced
    #  extend flag  Defines if a block should extend to its block size
    regs.WordSize  = regs.Metadata.retrieve("MemoryLayout").Tags["word_size"].Value
    bsize          = regs.Metadata.retrieve("MemoryLayout").Tags["block_size"].Value
    if bsize % regs.WordSize != 0:
        raise ValueError("Wordsize Doesnt Fit Into Block Size!")
    regs.BlockSize = bsize
    regs.Align     = regs.Metadata.retrieve("MemoryLayout").Tags["align"].Value
    regs.Extend    = regs.Metadata.retrieve("MemoryLayout").Tags["extend"].Value
    print("Metadata Extracted")
    print(f"Word size is {regs.WordSize} bytes")
    print(f"Block size is {regs.BlockSize} bytes")
    print(f"Align on word boundaries is {regs.Align}")
    print(f"Extend to block size is {regs.Extend}")
    print("")
    
    
    sys_offset = 0
    for sys in regs.Systems:
        
        # Pass 1 - For each register, convert tags into class attributes
        for reg in sys.unroll(Register):
            reg.tags_to_attributes()
        for group in sys.unroll(Group):
            group.tags_to_attributes()
            
    for sys in regs.Systems:
        # Pass 2A - For each register, compute the required size and offset
        print(f"Parsing System {sys.Name} for sizes and offsets")
        print(SPACER + "Register Sizes")
        for reg in sys.unroll(Register):
            reg.calc_size()
        print(SPACER + "Register Offsets")
        next_offset = sys_offset
        for reg in sys.unroll(Register):
            next_offset = reg.calc_offset(next_offset, regs.WordSize, regs.Align)
            
        # Pass 2B - For each register group (including the systems), compute
        #           the required size and offset
        print(SPACER + "Register Group Sizes")
        for group in sys.unroll(Group):
            if group is sys:
                group.calc_size(regs.WordSize, regs.Align, regs.BlockSize)
            else:
                group.calc_size(regs.WordSize, regs.Align)
        print(SPACER + "Register Group Offsets")
        for group in sys.unroll(Group):
            group.calc_offset(regs.WordSize, regs.Align)
        sys_offset += sys.AllocatedSize
        print("")
        
    regs.calc_size()
        
    const_lines = []
    if not use_literals:
        for sys in regs.Systems:
            # Pass 3A - For each register generate a line of micropython code that
            #           defines a micropython.const() object.
            for reg in sys.unroll(Register):
                const_lines.append(reg.const_name(f"OFFSET = const({reg.Offset})"))
                const_lines.append(reg.const_name(f"SIZE = const({reg.Size})"))
            const_lines.append("")
            # Pass 3B - For each register group generate a line of micropython code
            #           that defines a micropython.const() object.
            for group in sys.unroll(Group):
                const_lines.append(group.const_name(f"OFFSET = const({group.Offset})"))
                const_lines.append(group.const_name(f"ALLOC_SIZE = const({group.AllocatedSize})"))
                const_lines.append(group.const_name(f"USED_SIZE = const({group.UsedSize})"))
            const_lines.append("")
        
    const_lines.append(f"REG_MAP_ALLOC_SIZE = const({regs.TotalSize})")
    const_lines.append("")
    
    const_lines.append("buf = bytearray(REG_MAP_ALLOC_SIZE)")
    const_lines.append("")
    
    const_lines.append("def hexdump():")
    const_lines.append("    for i, b in enumerate(buf):")
    const_lines.append("        # Print byte as 2-digit hex with trailing space")
    const_lines.append("        print(f'{b:02x}', end=' ')")
    const_lines.append("        ")
    const_lines.append("        # New line after every 4th byte")
    const_lines.append("        if (i + 1) % 4 == 0:")
    const_lines.append("            print()")
    const_lines.append("")
    
    struct_lines = []
    for sys in regs.Systems:
        # Pass 4A - For each register and register group generate a field in a
        #           uctypes.struct object
        for group in reversed(sys.retrieve("Registers").unroll(Group)):
            if group is sys.retrieve("Registers"):
                struct_name = pascal_case_to_prefix(sys.Name)
            else:
                struct_name = pascal_case_to_prefix(sys.Name) + group.Name[:3]
            if private_dicts:
                struct_name = "_" + struct_name
            struct_lines.append(f"{struct_name.upper()} = {{")
            
            if use_literals:
                group_offset = group.Offset
            else:
                group_offset = group.const_name("OFFSET")
            
            for subgroup in group.Groups:
                if use_literals:
                    relative_offset = subgroup.Offset - group.Offset
                else:
                    relative_offset = f"{subgroup.const_name("OFFSET")}-{group_offset}"
                
                s_line = f"    '{subgroup.Name}' : "
                if isinstance(subgroup, Group):
                    s_line += f"({relative_offset}, "
                    if private_dicts:
                        s_line += "_"
                    s_line +=f"{pascal_case_to_prefix(sys.Name)+subgroup.Name[:3].upper()}),"
                elif isinstance(subgroup, Register):
                    s_line += f"uctypes.{subgroup.Type} | ({relative_offset}),"
                struct_lines.append(s_line)
            
            struct_lines.append("}")
            if use_substructs or group is sys.retrieve("Registers"):
                if private_dicts:
                    s_line =  f"{struct_name[1:].lower()} = uctypes.struct("
                else:
                    s_line =  f"{struct_name.lower()} = uctypes.struct("
                s_line += f"uctypes.addressof(buf)+{group_offset}, "
                s_line += f"{struct_name.upper()}, uctypes.NATIVE)"
                struct_lines.append(s_line)
            struct_lines.append("")
            
    for sys in regs.Systems:
        # Pass 4B - For each register group generate a numpy aray
        for group in sys.unroll(Group):
            
            if use_literals:
                group_offset = group.Offset
                group_count = group.AllocatedSize // 4
            else:
                group_offset = group.const_name("OFFSET")
                group_count = f"{group.const_name("ALLOC_SIZE")}//4"
            
            if group.Alias is not None:
                struct_lines.append(f"{pascal_case_to_prefix(sys.Name).lower()}_{group.Alias} = _array_view(buf, "
                                    f"{group_offset}, {group_count}, ({group_count}, ))")
    
    
    lines = []
    lines.append("from micropython import const")
    lines.append("from ulab import numpy as np")
    lines.append("import uctypes")
    lines.append("")
    
    
    lines.append("def _array_view(buf, offset, count, shape):")
    lines.append("    # Allocate ndarray views once during setup. Runtime code should reuse the")
    lines.append("    # returned objects instead of calling frombuffer in hot paths.")
    lines.append("    array = np.frombuffer(buf, dtype=np.float, count=count, offset=offset)")
    lines.append("    return array.reshape(shape)")
    lines.append("")
    
    lines.extend(const_lines) 
    
    lines.append("")
    
    lines.extend(struct_lines) 
    
    lines.append("")
    
    out = Path(output_filename)
    out.write_text("\r".join(lines))
    
    return regs, lines



if __name__ == "__main__":
    regs, lines = build_map()
    print("\r\n".join(lines))