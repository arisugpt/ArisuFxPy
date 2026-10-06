import os
import sys
import json
import struct

# Smart import for ArisuFxPy (with folder-shadowing fix & fallback)
try:
    import ArisuFxPy
    # If shadowed by parent directory named 'ArisuFxPy'
    if not hasattr(ArisuFxPy, "load"):
        try:
            import ArisuFxPy.ArisuFxPy as _mod
            ArisuFxPy = _mod
        except ImportError:
            pass
except ImportError:
    try:
        # Fallback to UnityPy if ArisuFxPy is not yet installed on mobile/Termux
        import UnityPy as ArisuFxPy
    except ImportError:
        print("[-] Error: Neither 'ArisuFxPy' nor 'UnityPy' is installed!")
        print("[-] To install ArisuFxPy on Termux/PC, run:")
        print("    pip install git+https://github.com/arisugpt/ArisuFxPy.git\n")
        sys.exit(1)

# Safe tabulate import
try:
    from tabulate import tabulate
except ImportError:
    def tabulate(data, headers, tablefmt="grid"):
        lines = ["\t".join(headers), "-" * 50]
        for row in data:
            lines.append("\t".join(str(c) for c in row))
        return "\n".join(lines)

def get_download_path():
    termux_down = "/sdcard/Download"
    if os.path.exists(termux_down):
        return termux_down
    return os.path.expanduser("~/Downloads")

def is_valid_unity_file(file_path):
    """Checks header signatures and magic bytes for valid Unity asset/bundle files"""
    try:
        with open(file_path, "rb") as f:
            header = f.read(32)
            if len(header) < 16:
                return False
            bundle_signatures = [b"UnityFS", b"UnityRaw", b"UnityWeb", b"UnityArchive"]
            for sig in bundle_signatures:
                if header.startswith(sig):
                    return True
            meta_size, file_size, format_ver = struct.unpack(">III", header[:12])
            if 9 <= format_ver <= 30 and (file_size > meta_size or file_size == 0):
                return True
    except Exception:
        return False
    return False

def dict_to_simple_txt(data, indent=0):
    lines = []
    prefix = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and not v:
                lines.append(f"{prefix}{k} = {{}}")
            elif isinstance(v, list) and not v:
                lines.append(f"{prefix}{k} = []")
            elif isinstance(v, (dict, list)):
                lines.append(f"{prefix}{k}")
                lines.append(dict_to_simple_txt(v, indent + 1))
            else:
                lines.append(f"{prefix}{k} = {json.dumps(v)}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict) and not item:
                lines.append(f"{prefix}[{i}] = {{}}")
            elif isinstance(item, list) and not item:
                lines.append(f"{prefix}[{i}] = []")
            elif isinstance(item, (dict, list)):
                lines.append(f"{prefix}[{i}]")
                lines.append(dict_to_simple_txt(item, indent + 1))
            else:
                lines.append(f"{prefix}[{i}] = {json.dumps(item)}")
    return "\n".join(lines)

def parse_simple_txt(text):
    root = {}
    stack = [(root, -1)]
    
    for line in text.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        while stack and stack[-1][1] >= indent:
            stack.pop()

        parent = stack[-1][0]

        if "=" in content:
            key, val = content.split("=", 1)
            val_str = val.strip()
            try:
                parsed_val = json.loads(val_str)
            except Exception:
                parsed_val = val_str
            parent[key.strip()] = parsed_val
        else:
            new_dict = {}
            if isinstance(parent, dict):
                parent[content] = new_dict
            stack.append((new_dict, indent))
            
    def rebuild_lists(node):
        if isinstance(node, dict):
            for k in list(node.keys()):
                node[k] = rebuild_lists(node[k])
            
            if len(node) > 0:
                keys = list(node.keys())
                if all(isinstance(k, str) and k.startswith('[') and k.endswith(']') and k[1:-1].isdigit() for k in keys):
                    sorted_keys = sorted(keys, key=lambda x: int(x[1:-1]))
                    return [node[k] for k in sorted_keys]
            return node
        elif isinstance(node, list):
            return [rebuild_lists(x) for x in node]
        else:
            return node
            
    return rebuild_lists(root)

def resolve_asset_name(obj, env):
    try:
        data = obj.read()
        if hasattr(data, "name") and data.name:
            return data.name
    except Exception:
        pass
    try:
        tree = obj.read_typetree()
        if isinstance(tree, dict):
            if "m_Name" in tree and tree["m_Name"]:
                return tree["m_Name"]
            if "m_GameObject" in tree:
                go_pid = tree["m_GameObject"].get("m_PathID")
                if go_pid:
                    for sub_obj in env.objects:
                        if sub_obj.path_id == go_pid:
                            go_tree = sub_obj.read_typetree()
                            if "m_Name" in go_tree and go_tree["m_Name"]:
                                return f"{go_tree['m_Name']} ({obj.type.name})"
    except Exception:
        pass
    return "Unnamed asset"

def dump_info_table(env, base_name, out_dir):
    table_data = []
    print("[*] Parsing asset names and creating index table...")
    for obj in env.objects:
        name = resolve_asset_name(obj, env)
        table_data.append([
            name,
            obj.type.name,
            obj.path_id,
            obj.byte_size
        ])

    headers = ["Asset Name", "Type", "Path ID", "Size (Bytes)"]
    formatted_table = tabulate(table_data, headers=headers, tablefmt="grid")
    
    out_file = os.path.join(out_dir, f"{base_name}_info_table.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(formatted_table)
    
    print(f"[+] Info Table saved: {out_file}")

def parse_path_ids(input_str):
    pids = []
    parts = input_str.split(",")
    for p in parts:
        clean = p.strip()
        if clean:
            try:
                pids.append(int(clean))
            except ValueError:
                print(f"[-] Skipped invalid Path ID format: {clean}")
    return pids

def main():
    file_path = input("Enter Asset/Bundle File Path: ").strip().strip('"').strip("'")
    if not os.path.isfile(file_path):
        print("[-] File not found!")
        return

    if not is_valid_unity_file(file_path):
        print("[-] Error: This doesn't seem to be an assets file or bundle.")
        return

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_dir = get_download_path()

    print("\n[*] Loading & Decompressing Bundle via ArisuFxPy...")
    try:
        env = ArisuFxPy.load(file_path)
    except Exception as e:
        print(f"[-] Load failed: {e}")
        return

    dump_info_table(env, base_name, out_dir)
    obj_dict = {obj.path_id: obj for obj in env.objects}

    while True:
        print("\n" + "="*40)
        print("ARISUFXPY BUNDLE MODDER OPTIONS:")
        print("1. Export Dump (.txt / .json)")
        print("2. Import Dump (.txt / .json)")
        print("3. Export Raw Asset Data (.dat)")
        print("4. Import Raw Asset Data (.dat)")
        print("5. Save & Compress (LZ4 / LZMA / None)")
        print("6. Exit")
        print("="*40)
        
        choice = input("Select option (1-6): ").strip()

        if choice == "1":
            pid_input = input("Enter Path ID to Export (e.g. ID1, ID2): ").strip()
            pids = parse_path_ids(pid_input)
            if not pids:
                print("[-] No valid Path IDs provided!")
                continue

            fmt = input("Select Format - [1] Standard Text (.txt)  [2] JSON (.json): ").strip()
            exported_files = []
            for pid in pids:
                if pid in obj_dict:
                    obj = obj_dict[pid]
                    try:
                        tree_data = obj.read_typetree()
                        if fmt == "1":
                            txt_content = dict_to_simple_txt(tree_data)
                            out_p = os.path.join(out_dir, f"{base_name}_{pid}_dump.txt")
                            with open(out_p, "w", encoding="utf-8") as f:
                                f.write(txt_content)
                        else:
                            out_p = os.path.join(out_dir, f"{base_name}_{pid}_dump.json")
                            with open(out_p, "w", encoding="utf-8") as f:
                                json.dump(tree_data, f, indent=4)
                        exported_files.append(out_p)
                    except Exception as e:
                        print(f"[-] Export Error for ID {pid}: {e}")
                else:
                    print(f"[-] Path ID {pid} not found in bundle!")

            if exported_files:
                print("[+] Exported successfully:")
                for ef in exported_files:
                    print(f"    {ef}")

        elif choice == "2":
            pid_input = input("Enter Path ID to Import (e.g. ID1, ID2): ").strip()
            pids = parse_path_ids(pid_input)
            if not pids:
                print("[-] No valid Path IDs provided!")
                continue

            dump_in = input("Enter File Path (.txt / .json): ").strip().strip('"').strip("'")
            if not os.path.isfile(dump_in):
                print("[-] File not found!")
                continue

            try:
                if dump_in.endswith(".json"):
                    with open(dump_in, "r", encoding="utf-8") as f:
                        new_tree = json.load(f)
                else:
                    with open(dump_in, "r", encoding="utf-8") as f:
                        new_tree = parse_simple_txt(f.read())
            except Exception as e:
                print(f"[-] Failed to read/parse dump file: {e}")
                continue

            patched_ids = []
            for pid in pids:
                if pid in obj_dict:
                    obj = obj_dict[pid]
                    try:
                        obj.save_typetree(new_tree)
                        patched_ids.append(str(pid))
                    except Exception as err:
                        print(f"[-] Patch Error for ID {pid}: {err}")
                else:
                    print(f"[-] Path ID {pid} not found in bundle!")

            if patched_ids:
                print(f"[+] Successfully patched into Path ID: {', '.join(patched_ids)}")

        elif choice == "3":
            pid_input = input("Enter Path ID to Export Raw (e.g. ID1, ID2): ").strip()
            pids = parse_path_ids(pid_input)
            if not pids:
                print("[-] No valid Path IDs provided!")
                continue

            for pid in pids:
                if pid in obj_dict:
                    obj = obj_dict[pid]
                    try:
                        raw_data = obj.get_raw_data()
                        raw_out = os.path.join(out_dir, f"{base_name}_{pid}_raw.dat")
                        with open(raw_out, "wb") as f:
                            f.write(raw_data)
                        print(f"[+] Raw data saved to: {raw_out}")
                    except Exception as e:
                        print(f"[-] Raw Export Error for {pid}: {e}")
                else:
                    print(f"[-] Path ID {pid} not found!")

        elif choice == "4":
            pid_input = input("Enter Path ID to Import Raw (e.g. ID1, ID2): ").strip()
            pids = parse_path_ids(pid_input)
            if not pids:
                print("[-] No valid Path IDs provided!")
                continue

            raw_in = input("Enter Raw .dat File Path: ").strip().strip('"').strip("'")
            if not os.path.isfile(raw_in):
                print("[-] Raw file not found!")
                continue

            try:
                with open(raw_in, "rb") as f:
                    new_raw = f.read()
            except Exception as e:
                print(f"[-] Read Error: {e}")
                continue

            patched_ids = []
            for pid in pids:
                if pid in obj_dict:
                    obj = obj_dict[pid]
                    try:
                        obj.set_raw_data(new_raw)
                        patched_ids.append(str(pid))
                    except Exception as e:
                        print(f"[-] Raw Import Error for {pid}: {e}")
                else:
                    print(f"[-] Path ID {pid} not found!")

            if patched_ids:
                print(f"[+] Raw data patched into Path ID: {', '.join(patched_ids)}")

        elif choice == "5":
            print("\nCompression Modes: [1] LZ4  [2] LZMA  [3] None (Uncompressed)")
            comp_choice = input("Select compression (1/2/3): ").strip()
            packer_type = "lz4" if comp_choice == "1" else ("lzma" if comp_choice == "2" else "none")
            
            save_name = input("Enter output file name: ").strip()
            save_dest = os.path.join(out_dir, save_name)

            try:
                with open(save_dest, "wb") as f:
                    f.write(env.file.save(packer=packer_type))
                print(f"[+] Bundle re-packed and saved: {save_dest}")
            except Exception as e:
                print(f"[-] Save Error: {e}")

        elif choice == "6":
            print("[*] Exiting script.")
            break
        else:
            print("[-] Invalid option.")

if __name__ == "__main__":
    main()
