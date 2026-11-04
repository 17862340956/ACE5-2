#!/usr/bin/env python3
"""Validate the real 6.1 module against build inputs and supplied target evidence."""
from pathlib import Path
import hashlib
import json
import struct
import sys
from elftools.elf.elffile import ELFFile
from fix_vermagic import entries, field

EXPECTED_ARGS = {
    'fake_available': ['cpufreq_policy *', 'char *'],
    'fake_topology': ['device *', 'device_attribute *', 'char *'],
    'fake_cpu_mask': ['device *', 'device_attribute *', 'char *'],
    'fake_cpuinfo_open': ['inode *', 'file *'],
    'fake_cpuinfo_show': ['seq_file *', 'void *'],
    'fake_cpuinfo_start': ['seq_file *', 'long long *'],
    'fake_cpuinfo_next': ['seq_file *', 'void *', 'long long *'],
    'fake_cpuinfo_stop': ['seq_file *', 'void *'],
    'status_open': ['inode *', 'file *'],
    'status_show': ['seq_file *', 'void *'],
}


def typename(die):
    if die is None:
        return 'void'
    if die.tag in ('DW_TAG_typedef', 'DW_TAG_const_type', 'DW_TAG_volatile_type', 'DW_TAG_restrict_type'):
        return typename(die.get_DIE_from_attribute('DW_AT_type') if 'DW_AT_type' in die.attributes else None)
    if die.tag == 'DW_TAG_pointer_type':
        return typename(die.get_DIE_from_attribute('DW_AT_type') if 'DW_AT_type' in die.attributes else None) + ' *'
    name = die.attributes.get('DW_AT_name')
    if not name:
        return die.tag
    name = name.value.decode()
    return {'long long int': 'long long', 'long int': 'long',
            'long unsigned int': 'unsigned long', 'unsigned long int': 'unsigned long'}.get(name, name)


def signed_return(die, size):
    seen = set()
    while die is not None and die.tag in ('DW_TAG_typedef', 'DW_TAG_const_type', 'DW_TAG_volatile_type'):
        if die.offset in seen:
            return False
        seen.add(die.offset)
        die = die.get_DIE_from_attribute('DW_AT_type') if 'DW_AT_type' in die.attributes else None
    return bool(die and die.tag == 'DW_TAG_base_type' and
                die.attributes.get('DW_AT_byte_size') and die.attributes['DW_AT_byte_size'].value == size and
                die.attributes.get('DW_AT_encoding') and die.attributes['DW_AT_encoding'].value == 5)


def read_versions(elf):
    section = elf.get_section_by_name('__versions')
    if section is None or not section['sh_size']:
        raise ValueError('MODVERSIONS table missing or empty')
    raw = section.data()
    if len(raw) % 64:
        raise ValueError('malformed AArch64 modversion_info table')
    versions = {}
    for start in range(0, len(raw), 64):
        crc = struct.unpack_from('<Q', raw, start)[0]
        name_bytes = raw[start + 8:start + 64]
        if b'\0' not in name_bytes:
            raise ValueError('unterminated modversion symbol')
        name = name_bytes.split(b'\0', 1)[0].decode('ascii')
        if not name or name in versions or not 0 < crc <= 0xffffffff:
            raise ValueError('invalid or duplicate CRC entry: ' + name)
        versions[name] = crc
    if 'module_layout' not in versions:
        raise ValueError('module_layout CRC missing')
    return versions


def read_kcfi(symtab):
    return {s.name[len('__kcfi_typeid_'):]: s['st_value'] for s in symtab.iter_symbols()
            if s.name.startswith('__kcfi_typeid_') and s['st_shndx'] == 'SHN_ABS'}


def read_callback_kcfi(elf, names):
    """AArch64 KCFI hashes live at function_address - 4.

    __kcfi_typeid_* absolute symbols are optional, especially for local C
    callbacks. When retained, they must agree with the actual prefix word.
    """
    symtab = elf.get_section_by_name('.symtab')
    if symtab is None:
        raise ValueError('symbol table required for KCFI function lookup')
    absolute = read_kcfi(symtab)
    values = {}
    evidence = {}
    for name in names:
        candidates = [s for s in (symtab.get_symbol_by_name(name) or [])
                      if s['st_info']['type'] == 'STT_FUNC' and isinstance(s['st_shndx'], int)]
        locations = {(s['st_shndx'], s['st_value']) for s in candidates}
        if len(locations) != 1:
            raise ValueError('missing or ambiguous callback function symbol: ' + name)
        section_index, address = next(iter(locations))
        section = elf.get_section(section_index)
        if not section['sh_flags'] & 4:
            raise ValueError('callback is not in executable code: ' + name)
        offset = address - section['sh_addr']
        code = section.data()
        if offset < 4 or offset >= len(code):
            raise ValueError('callback KCFI prefix outside section: ' + name)
        value = struct.unpack_from('<I', code, offset - 4)[0]
        if name in absolute and absolute[name] != value:
            raise ValueError('callback KCFI symbol/prefix disagreement: ' + name)
        values[name] = value
        evidence[name] = {'source': 'arm64-function-prefix', 'section': section.name,
                          'function_offset': offset, 'hash_offset': offset - 4,
                          'named_typeid_symbol_present': name in absolute}
    return values, evidence


def compare_known(actual, known, label):
    shared = sorted(actual.keys() & known.keys())
    mismatch = [{'symbol': name, 'module': f'0x{actual[name]:08x}', 'target': known[name]}
                for name in shared if actual[name] != int(known[name], 16)]
    if mismatch:
        raise ValueError(label + ' mismatch: ' + json.dumps(mismatch))
    return shared


def validate(module, root=None):
    root = Path(root) if root else Path(__file__).resolve().parent
    target = json.loads((root / 'TARGET_PROFILE.json').read_text())
    btf = json.loads((root / 'TARGET_BTF.json').read_text())
    data = module.read_bytes()
    info = entries(data)
    metadata = {key: field(info, key.encode()).decode() for key in
                ('name', 'version', 'vermagic', 'source_basis', 'target_btf_sha256')}
    if metadata['name'] != 'cpuinfo_spoof' or metadata['version'] != target['revision']:
        raise ValueError('wrong module identity')
    if metadata['vermagic'].split() != [target['target_release']] + target['vermagic_flags'].split():
        raise ValueError('wrong target release or module configuration flags')
    if metadata['source_basis'] != 'PKG110_BTF_PROFILE' or metadata['target_btf_sha256'] != target['btf_sha256']:
        raise ValueError('wrong target BTF identity')
    with module.open('rb') as stream:
        elf = ELFFile(stream)
        if elf['e_machine'] != 'EM_AARCH64' or elf['e_type'] != 'ET_REL' or elf.elfclass != 64 or not elf.little_endian:
            raise ValueError('expected AArch64 ELF64 ET_REL')
        if not elf.has_dwarf_info():
            raise ValueError('unstripped DWARF required')
        callbacks = {}
        for cu in elf.get_dwarf_info().iter_CUs():
            for die in cu.iter_DIEs():
                name = die.attributes.get('DW_AT_name')
                if die.tag != 'DW_TAG_subprogram' or not name or name.value.decode(errors='replace') not in EXPECTED_ARGS:
                    continue
                name = name.value.decode()
                params = [c for c in die.iter_children() if c.tag == 'DW_TAG_formal_parameter']
                if not params or any('DW_AT_type' not in p.attributes for p in params):
                    continue
                args = [typename(p.get_DIE_from_attribute('DW_AT_type')) for p in params]
                if args != EXPECTED_ARGS[name]:
                    raise ValueError('callback parameter mismatch: ' + name + ' ' + str(args))
                ret = die.get_DIE_from_attribute('DW_AT_type') if 'DW_AT_type' in die.attributes else None
                if name in ('fake_cpuinfo_start', 'fake_cpuinfo_next'):
                    return_ok = typename(ret) == 'void *'
                elif name == 'fake_cpuinfo_stop':
                    return_ok = typename(ret) == 'void'
                else:
                    return_ok = signed_return(ret, 4 if name in ('fake_cpuinfo_open', 'fake_cpuinfo_show', 'status_open', 'status_show') else 8)
                if not return_ok:
                    raise ValueError('callback return type mismatch: ' + name)
                callbacks[name] = args
        if set(callbacks) != set(EXPECTED_ARGS):
            raise ValueError('missing callback DWARF: ' + str(set(EXPECTED_ARGS) - set(callbacks)))
        symtab = elf.get_section_by_name('.symtab')
        if symtab is None:
            raise ValueError('symbol table required')
        kcfi = read_kcfi(symtab)
        callback_ids, callback_kcfi_evidence = read_callback_kcfi(elf, EXPECTED_ARGS)
        kcfi_matches = compare_known(kcfi, target['known_kcfi_typeids'], 'sampled KCFI type ID')
        # The native single_release has the same exact prototype as proc_open.
        # Other callback hashes have no native sample evidence; keep that gap explicit.
        role_matches = {}
        expected_open_id = int(target['known_kcfi_typeids']['single_release'], 16)
        for name in ('fake_cpuinfo_open', 'status_open'):
            if callback_ids[name] != expected_open_id:
                raise ValueError('target proc-open KCFI hash mismatch: ' + name)
            role_matches[name] = {'native_equivalent': 'single_release', 'typeid': f'0x{expected_open_id:08x}'}
        versions = read_versions(elf)
        crc_matches = compare_known(versions, target['known_symbol_crcs'], 'sampled target CRC')
        if 'module_layout' not in crc_matches:
            raise ValueError('target module_layout CRC was not checked')
        undefined = sorted({s.name for s in symtab.iter_symbols()
                            if s.name and s['st_shndx'] == 'SHN_UNDEF' and s['st_info']['bind'] != 'STB_WEAK'})
        if any(n not in versions for n in undefined):
            raise ValueError('unversioned required imports: ' + str([n for n in undefined if n not in versions]))
        values = symtab.get_symbol_by_name('opd2407_layout_values')
        if not values or len(values) != 1:
            raise ValueError('target offset evidence array missing')
        symbol = values[0]
        section = elf.get_section(symbol['st_shndx'])
        raw = section.data()[symbol['st_value']:symbol['st_value'] + symbol['st_size']]
        def offset(structure, member):
            return next(m['byte_offset'] for m in btf['layouts'][structure]['members'] if m['name'] == member)
        if not any(m['name'] == '' and m['byte_offset'] == 48 for m in btf['layouts']['proc_dir_entry']['members']):
            raise ValueError('target proc_ops union evidence missing')
        expected = [offset('uts_namespace', 'name'), offset('device', 'id'),
                    offset('dentry', 'd_inode'), offset('inode', 'i_mode'),
                    offset('inode', 'i_sb'), offset('inode', 'i_ino'),
                    offset('super_block', 's_magic'), btf['layouts']['rw_semaphore']['size'],
                    offset('proc_inode', 'vfs_inode'), offset('proc_inode', 'pde'),
                    btf['layouts']['proc_dir_entry']['size'], 48,
                    offset('proc_dir_entry', 'low_ino'), offset('proc_dir_entry', 'parent'),
                    offset('proc_dir_entry', 'name'), offset('proc_dir_entry', 'mode'),
                    offset('proc_dir_entry', 'flags')]
        if len(raw) != 8 * len(expected) or list(struct.unpack('<' + 'Q' * len(expected), raw)) != expected:
            raise ValueError('compiled target offset evidence differs from live BTF')
    logs = root / 'build_logs'
    config = (logs / 'ddk.config').read_bytes()
    config_text = config.decode()
    for option in ('CONFIG_CFI_CLANG=y', 'CONFIG_MODVERSIONS=y', 'CONFIG_COMPAT=y', 'CONFIG_SHADOW_CALL_STACK=y'):
        if option not in config_text.splitlines():
            raise ValueError('missing required build configuration: ' + option)
    symvers = {}
    for line in (logs / 'Module.symvers').read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2:
            value = int(fields[0], 16)
            if fields[1] in symvers and symvers[fields[1]] != value:
                raise ValueError('conflicting DDK CRC for ' + fields[1])
            symvers[fields[1]] = value
    if any(symvers.get(n) != crc for n, crc in versions.items()):
        raise ValueError('module version table differs from actual DDK Module.symvers')
    image = json.loads((logs / 'image-inspect.json').read_text())[0]
    unknown = sorted(set(versions) - set(crc_matches))
    return {
        'validation': 'passed', 'file': module.name, 'revision': target['revision'],
        'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
        'vermagic': metadata['vermagic'], 'target_device': 'PKG110', 'target_platform': 'pineapple',
        'target_btf_sha256': target['btf_sha256'], 'source_basis': metadata['source_basis'],
        'callbacks': callbacks, 'dwarf': 'passed', 'cfi_mode': 'kcfi',
        'callback_kcfi_typeids': {n: f'0x{callback_ids[n]:08x}' for n in EXPECTED_ARGS},
        'callback_kcfi_evidence': callback_kcfi_evidence,
        'sampled_kcfi_matches': kcfi_matches, 'callback_target_kcfi_matches': role_matches,
        'target_kcfi_unverified_callbacks': sorted(set(EXPECTED_ARGS) - set(role_matches)),
        'full_target_callback_kcfi_proof': False, 'module_version_entries': len(versions),
        'target_sample_crc_matches': crc_matches, 'target_crc_unverified_symbols': unknown,
        'full_target_crc_proof': not unknown, 'target_offset_evidence': expected,
        'compiled_public_layout_assertions': 'passed', 'runtime': 'not tested',
        'build_inputs': {'image_id': image['Id'], 'image_repo_digests': image.get('RepoDigests', []),
                         'config_sha256': hashlib.sha256(config).hexdigest(),
                         'module_symvers_sha256': hashlib.sha256((logs / 'Module.symvers').read_bytes()).hexdigest(),
                         'kit_manifest_sha256': hashlib.sha256((root / 'KIT_MANIFEST.json').read_bytes()).hexdigest()},
        'limits': 'Target CRC evidence covers vendor samples only. BTF does not prove runtime object addresses or write permissions.'
    }


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: report.py MODULE.ko REPORT.json')
    output = Path(sys.argv[2])
    try:
        result = validate(Path(sys.argv[1]))
    except Exception as exc:
        output.write_text(json.dumps({'validation': 'failed', 'error': str(exc)}, indent=2) + '\n')
        sys.exit('KO_VERIFICATION_FAILED: ' + str(exc))
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
