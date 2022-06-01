from xml.etree import ElementTree, ElementInclude
import pathlib
import ranges
import sys

root_path = pathlib.Path("in")

tree = ElementTree.parse(pathlib.Path(sys.argv[1]))
root = tree.getroot()

namespaces = {
    "def": "http://www.arm.com/core_definition",
    "reg": "http://www.arm.com/core_reg",
    "tcf": "http://com.arm.targetconfigurationeditor"
}

ACCESS_TYPES = {
    "RW": "read-write",
    "RO": "read-only",
    "WO": "write-only"
}

def loader(href, parse):
    if parse == "xml":
        return ElementTree.parse(root_path / "Cores" / href).getroot()

ElementInclude.include(root, loader=loader)

enums = {}

# Load all of the enum info first
for e in root.iter("{http://com.arm.targetconfigurationeditor}enumeration"):
    ename = e.get("name")
    
    if ename in enums:
        # Assume enums with the same name are the same.
        continue
    values = e.get("values")
    enum_lines = ["<enumeratedValues>", f"  <name>{ename}</name>", f"  <headerEnumName>{ename}</headerEnumName>"]
    if values:
        for value in values.split(","):
            if not value:
                continue
            name, value = value.split("=")
            description = name.replace("_", " ")
            enum_lines.append(f"  <enumeratedValue><name>{name}</name><description>{description}</description><value>{value}</value></enumeratedValue>")
    else:
        description = e.find("tcf:description", namespaces=namespaces)
        if description:
            enum_lines.append(f"  <description>{description.text}</description>")
        for item in e.findall("tcf:enumItem", namespaces=namespaces):
            name = item.get("name")
            value = item.get("number")
            description = item.find("tcf:gui_name", namespaces=namespaces)
            if description:
                description = description.text
            else:
                description = name.replace("_", " ")
            enum_lines.append(f"  <enumeratedValue><name>{name}</name><description>{description}</description><value>{value}</value></enumeratedValue>")
    enum_lines.append("</enumeratedValues>")
    enums[ename] = [None, enum_lines]

cpu_name = root.find("def:name", namespaces=namespaces).text
cpu_id = cpu_name.replace("-", "_")
cpu_series = root.find("def:series", namespaces=namespaces).text

peripherals = {}
lines = [
f'<?xml version="1.0" encoding="UTF-8"?>',
f'<device xmlns:xs="http://www.w3.org/2001/XMLSchema-instance"',
f'        schemaVersion="1.3"',
f'        xs:noNamespaceSchemaLocation="https://raw.githubusercontent.com/ARM-software/CMSIS_5/develop/CMSIS/Utilities/CMSIS-SVD.xsd">',
f'  <vendor>ARM Ltd.</vendor>',
f'  <vendorID>ARM</vendorID>',
f'  <name>{cpu_id}</name>',
f'  <series>{cpu_series}</series>',
f'  <version>2020-08-22T15:13:24.354567-05:00</version>',
f'  <description>{cpu_name} core descriptions, generated from ARM Development studio</description>',
f'  <cpu>',
f'     <name>CM4</name>',
f'     <revision>r0p0</revision>',
f'     <endian>little</endian>',
f'     <nvicPrioBits>8</nvicPrioBits>',
f'     <vendorSystickConfig>true</vendorSystickConfig>',
f'  </cpu>',
f'  <addressUnitBits>8</addressUnitBits>',
f'  <width>32</width>',
f'  <peripherals>',
]

for p in root.iter("{http://www.arm.com/core_reg}peripheral"):
    pname, offset = p.get("name"), p.get("offset")
    if pname in peripherals:
        continue
    peripherals[pname] = {"name": pname, "offset": offset}
    pdescription = p.find("reg:description", namespaces=namespaces)
    print(pname, offset, pdescription.text)
    address_blocks = ranges.RangeSet()
    registers = []
    for child in p.findall("reg:register", namespaces=namespaces):
        register_lines = []
        name, access, size, offset = child.get("name"), child.get("access"), int(child.get("size")), int(child.get("offset"),0)
        print(name, access, size, hex(offset))
        register_lines.append(f"<name>{name}</name>")
        register_lines.append(f"<size>{size * 8}</size>")
        register_lines.append(f"<access>{ACCESS_TYPES[access]}</access>")
        address_blocks.add(ranges.Range(offset, offset + size))
        description = child.find("reg:description", namespaces=namespaces)
        register_lines.append(f"<description>{description.text}</description>")
        bits = child.findall("reg:bitField", namespaces=namespaces)
        if bits:
            register_lines.append("<fields>")
        for bit in bits:
            description = bit.find("reg:description", namespaces=namespaces)
            definition = bit.find("reg:definition", namespaces=namespaces)
            name = bit.get("name")
            register_lines.append(f"  <field>")
            register_lines.append(f"    <name>{name}</name>")
            register_lines.append(f"    <description>{description.text}</description>")
            if ":" in definition.text:
                register_lines.append(f"    <bitRange>{definition.text}</bitRange>")
            else:
                position = definition.text.strip("[]")
                register_lines.append(f"    <bitOffset>{position}</bitOffset>")
                register_lines.append(f"    <bitWidth>1</bitWidth>")
            #print(bit.get("name"), bit.get("enumerationId"), description.text, definition.text)
            enum_id = bit.get("enumerationId")
            if enum_id and enum_id in enums:
                previous, elines = enums[enum_id]
                if previous:
                    register_lines.append(f"    <enumeratedValues derivedFrom=\"{enum_id}\"/>")
                else:
                    register_lines.extend(("    " + l for l in elines))
                    enums[enum_id][0] = True
            register_lines.append(f"  </field>")
        if bits:
            register_lines.append("</fields>")
        registers.append((register_lines, offset))
        print()
    lines.append(f"  <peripheral>")
    lines.append(f"    <name>{pname}</name>")
    lines.append(f"    <description>{pdescription.text}</description>")
    base_address = address_blocks.ranges()[0].start
    lines.append(f"    <baseAddress>0x{base_address:08x}</baseAddress>")
    for block in address_blocks:
        offset = block.start - base_address
        size = block.end - block.start
        lines.append(f"    <addressBlock><offset>0x{offset:08x}</offset><size>0x{size:08x}</size><usage>registers</usage></addressBlock>")
    lines.append(f"    <registers>")
    for register_lines, address in registers:
        lines.append(f"      <register>")
        lines.extend(("        " + l for l in register_lines))
        offset = address - base_address
        lines.append(f"        <addressOffset>0x{offset}</addressOffset>")
        lines.append(f"        <addressOffset>0x{offset:x}</addressOffset>")
        lines.append(f"      </register>")
    lines.append(f"    </registers>")
    lines.append(f"  </peripheral>")
    print("---------------")
    print()


lines.append("</peripherals>")
lines.append("</device>")
lines.append("")

out = pathlib.Path(sys.argv[2])
out.write_text("\n".join(lines))
