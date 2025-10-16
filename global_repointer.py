import struct
import argparse
import os
import datetime

GBA_POINTER_BASE = 0x08000000
LOG_FILE_NAME = "global_repointer_log.txt"

def find_marker_offsets(rom_path, scan_start, scan_end, target_sequences, offset_in_sequence):
    """
    Encontra marcadores em uma ROM e retorna uma lista ordenada dos offsets alvo.
    """
    try:
        with open(rom_path, 'rb') as f:
            f.seek(scan_start)
            if scan_end != -1:
                buffer = f.read(scan_end - scan_start)
            else:
                buffer = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo ROM '{rom_path}' não encontrado.")
        return None
    except Exception as e:
        print(f"ERRO ao ler a ROM '{rom_path}': {e}")
        return None

    all_occurrences = []
    for seq_bytes in target_sequences:
        idx = -1
        while True:
            idx = buffer.find(seq_bytes, idx + 1)
            if idx == -1:
                break
            all_occurrences.append({'offset': idx, 'sequence': seq_bytes})
    
    all_occurrences.sort(key=lambda x: x['offset'])

    target_offsets = []
    for match in all_occurrences:
        # Valida o offset para a sequência específica encontrada
        if offset_in_sequence >= len(match['sequence']):
            print(f"AVISO: 'Offset na sequência' ({offset_in_sequence}) é inválido para a sequência encontrada '{match['sequence'].hex().upper()}' (comprimento {len(match['sequence'])}). Pulando esta ocorrência.")
            continue
        
        absolute_offset = scan_start + match['offset'] + offset_in_sequence
        target_offsets.append(absolute_offset)

    return target_offsets

def calculate_pointer_values(offsets, use_base):
    """Converte offsets de arquivo para valores de ponteiro GBA."""
    base = GBA_POINTER_BASE if use_base else 0
    return [offset + base for offset in offsets]

def global_find_and_replace(
    original_rom_path, translated_rom_path,
    original_scan_start_hex, original_scan_end_hex,
    translated_scan_start_hex, translated_scan_end_hex,
    target_bytes_list_hex_str,
    offset_in_sequence_val,
    use_base=True, quiet=False
):
    log_entries = []
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Cabeçalho do Log
    header_info = [
        f"Relatório de Execução - Mapeador e Substituidor Global de Ponteiros - {current_time}",
        f"ROM Original: {original_rom_path}",
        f"ROM Alvo (Traduzida): {translated_rom_path}",
        f"--------------------------------------------------------------------------------",
        f"Parâmetros de Análise:",
        f"  Sequências Alvo Buscadas: {target_bytes_list_hex_str.upper()}",
        f"  Deslocamento no Alvo: {offset_in_sequence_val}",
        f"  Usar Base GBA (0x{GBA_POINTER_BASE:08X}): {'Sim' if use_base else 'Não'}",
        f"  Janela de Busca na ROM Original: 0x{original_scan_start_hex.upper()} - 0x{original_scan_end_hex.upper() if original_scan_end_hex else 'EOF'}",
        f"  Janela de Busca na ROM Traduzida: 0x{translated_scan_start_hex.upper()} - 0x{translated_scan_end_hex.upper() if translated_scan_end_hex else 'EOF'}",
        f"--------------------------------------------------------------------------------"
    ]
    log_entries.extend(header_info)
    if not quiet:
        for line in header_info:
            print(line)

    try:
        # --- Validação e Conversão de Parâmetros ---
        original_scan_start = int(original_scan_start_hex, 16)
        original_scan_end = int(original_scan_end_hex, 16) if original_scan_end_hex else -1
        translated_scan_start = int(translated_scan_start_hex, 16)
        translated_scan_end = int(translated_scan_end_hex, 16) if translated_scan_end_hex else -1
        offset_in_sequence = int(str(offset_in_sequence_val), 0)
        
        # *** INÍCIO DA CORREÇÃO ***
        # Validação crucial adicionada para as janelas de busca
        if original_scan_end != -1 and original_scan_end <= original_scan_start:
            msg = f"\nERRO na ROM Original: O offset final de busca (0x{original_scan_end:X}) deve ser maior que o offset inicial (0x{original_scan_start:X})."
            log_entries.append(msg)
            if not quiet: print(msg)
            return

        if translated_scan_end != -1 and translated_scan_end <= translated_scan_start:
            msg = f"\nERRO na ROM Traduzida: O offset final de busca (0x{translated_scan_end:X}) deve ser maior que o offset inicial (0x{translated_scan_start:X})."
            log_entries.append(msg)
            if not quiet: print(msg)
            return
        # *** FIM DA CORREÇÃO ***

        target_hex_strings = [s.strip() for s in target_bytes_list_hex_str.split(',')]
        target_sequences_bytes = [bytes.fromhex(s) for s in target_hex_strings]
        
        # --- Passo 1 & 2: Analisar ambas as ROMs e criar listas de ponteiros ---
        if not quiet: print("\nAnalisando ROM Original para mapear ponteiros antigos...")
        old_target_offsets = find_marker_offsets(original_rom_path, original_scan_start, original_scan_end, target_sequences_bytes, offset_in_sequence)
        if old_target_offsets is None: return # Erro já foi impresso na função

        if not quiet: print(f"Encontrados {len(old_target_offsets)} marcadores na ROM Original.")
        
        if not quiet: print("\nAnalisando ROM Traduzida para mapear ponteiros novos...")
        new_target_offsets = find_marker_offsets(translated_rom_path, translated_scan_start, translated_scan_end, target_sequences_bytes, offset_in_sequence)
        if new_target_offsets is None: return

        if not quiet: print(f"Encontrados {len(new_target_offsets)} marcadores na ROM Traduzida.")

        # --- Passo 3: Criar o Mapa de "DE -> PARA" ---
        if len(old_target_offsets) != len(new_target_offsets):
            msg = (f"\nERRO CRÍTICO: O número de marcadores encontrados é diferente entre as ROMs!\n"
                   f"  - ROM Original: {len(old_target_offsets)} marcadores.\n"
                   f"  - ROM Traduzida: {len(new_target_offsets)} marcadores.\n"
                   f"  A operação não pode continuar de forma segura. Verifique suas janelas de busca e arquivos.")
            log_entries.append(msg)
            if not quiet: print(msg)
            return

        old_pointer_values = calculate_pointer_values(old_target_offsets, use_base)
        new_pointer_values = calculate_pointer_values(new_target_offsets, use_base)
        
        pointer_map = dict(zip(old_pointer_values, new_pointer_values))

        log_entries.append("\n== Mapa de Ponteiros 'DE -> PARA' Criado ==")
        log_entries.append(f"Total de {len(pointer_map)} pares mapeados.")
        log_entries.append("--------------------------------------------------------------------------------")
        log_entries.append("Valor Antigo (Int) | Bytes Antigos (LE)   | -> | Novo Valor (Int) | Novo Valor (Bytes LE)")
        log_entries.append("--------------------------------------------------------------------------------")
        for old_val, new_val in pointer_map.items():
            old_bytes_le_str = ' '.join(f'{b:02X}' for b in struct.pack('<I', old_val))
            new_bytes_le_str = ' '.join(f'{b:02X}' for b in struct.pack('<I', new_val))
            log_entries.append(f"0x{old_val:08X}         | {old_bytes_le_str:<18} | -> | 0x{new_val:08X}         | {new_bytes_le_str}")
        log_entries.append("--------------------------------------------------------------------------------")

        if not quiet:
            print("\n== Mapa de Ponteiros 'DE -> PARA' Criado com sucesso. ==")
            print("Iniciando busca e substituição global na ROM Traduzida...")

        # --- Passo 4: Buscar e Substituir Globalmente na ROM Traduzida ---
        try:
            with open(translated_rom_path, 'rb') as f:
                # Usar bytearray porque é mutável, mais eficiente para múltiplas substituições
                rom_data = bytearray(f.read())
        except Exception as e:
            msg = f"ERRO ao ler o arquivo da ROM Traduzida para modificação: {e}"
            log_entries.append(msg)
            if not quiet: print(msg)
            return

        total_replacements = 0
        log_entries.append("\n== Relatório de Substituições Globais ==")
        log_entries.append("Substituindo o ponteiro antigo... | ...pelo ponteiro novo... | ...no endereço (offset) da ROM Alvo.")
        log_entries.append("--------------------------------------------------------------------------------")
        
        for old_val, new_val in pointer_map.items():
            old_bytes_le = struct.pack('<I', old_val)
            new_bytes_le = struct.pack('<I', new_val)
            
            start_pos = 0
            replacements_for_this_pointer = 0
            while True:
                idx = rom_data.find(old_bytes_le, start_pos)
                if idx == -1:
                    break
                
                # Realiza a substituição na memória
                rom_data[idx:idx+4] = new_bytes_le
                
                log_line = f"0x{old_val:08X} ({old_bytes_le.hex(' ').upper()}) | 0x{new_val:08X} ({new_bytes_le.hex(' ').upper()}) | 0x{idx:08X}"
                log_entries.append(log_line)
                
                replacements_for_this_pointer += 1
                start_pos = idx + 4 # Continua a busca após a posição atual

            if not quiet and replacements_for_this_pointer > 0:
                print(f"  - Ponteiro 0x{old_val:08X} substituído {replacements_for_this_pointer} vez(es).")
            
            total_replacements += replacements_for_this_pointer
        
        if total_replacements == 0:
            msg = "\nAVISO: Nenhuma ocorrência dos ponteiros antigos foi encontrada na ROM Alvo para substituição. Nenhuma modificação foi escrita."
            log_entries.append(msg)
            if not quiet: print(msg)
            return

        # --- Passo 5: Escrever as alterações de volta no arquivo ---
        try:
            with open(translated_rom_path, 'wb') as f:
                f.write(rom_data)
        except Exception as e:
            msg = f"ERRO CRÍTICO ao escrever as alterações de volta na ROM Alvo: {e}"
            log_entries.append(msg)
            if not quiet: print(msg)
            return

        summary_msg = f"\nOperação concluída com sucesso. Total de {total_replacements} substituições realizadas."
        log_entries.append("\n--------------------------------------------------------------------------------")
        log_entries.append(summary_msg)
        if not quiet: print(summary_msg)

    except Exception as e:
        msg = f"\nERRO INESPERADO DURANTE A EXECUÇÃO: {e}"
        log_entries.append(msg)
        if not quiet: print(msg)
        import traceback
        log_entries.append(traceback.format_exc())
    finally:
        # Escreve o log
        try:
            with open(LOG_FILE_NAME, 'w', encoding='utf-8') as log_f:
                for entry in log_entries:
                    log_f.write(entry + "\n")
            if not quiet and os.path.exists(LOG_FILE_NAME):
                print(f"Log detalhado salvo em: {LOG_FILE_NAME}")
        except Exception as e_log:
            print(f"ERRO CRÍTICO AO ESCREVER O ARQUIVO DE LOG '{LOG_FILE_NAME}': {e_log}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="global_repointer.py",
        description="Mapeia ponteiros entre uma ROM original e uma traduzida, e depois realiza uma substituição global de todos os ponteiros antigos pelos novos na ROM traduzida.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Argumentos para ROMs
    parser.add_argument("original_rom", help="Caminho para o arquivo da ROM original.")
    parser.add_argument("translated_rom", help="Caminho para o arquivo da ROM traduzida (alvo da modificação).")
    
    # Argumentos para busca
    parser.add_argument("original_scan_start", help="Offset (hex) de início da busca na ROM original.")
    parser.add_argument("translated_scan_start", help="Offset (hex) de início da busca na ROM traduzida.")
    parser.add_argument("target_bytes_list", help="LISTA de sequências de bytes (hex), separadas por VÍRGULA, a serem buscadas. Ex: '00FB,02FB'")

    # Argumentos opcionais
    parser.add_argument("--original_scan_end", "-ose", default=None, help="(Opcional) Offset (hex) de fim da busca na ROM original.")
    parser.add_argument("--translated_scan_end", "-tse", default=None, help="(Opcional) Offset (hex) de fim da busca na ROM traduzida.")
    parser.add_argument("--offset-in-sequence", default="1", help="Deslocamento (dec ou hex) dentro da sequência alvo encontrada. Padrão: 1 (para XXFB -> FB).")
    parser.add_argument("--no-base", action="store_false", dest="use_base", help="Não usar a base GBA (0x08000000) ao calcular os valores dos ponteiros.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Modo silencioso. Mostra menos informações no console.")

    parser.set_defaults(use_base=True)
    args = parser.parse_args()

    global_find_and_replace(
        args.original_rom, args.translated_rom,
        args.original_scan_start, args.original_scan_end,
        args.translated_scan_start, args.translated_scan_end,
        args.target_bytes_list,
        args.offset_in_sequence,
        args.use_base, args.quiet
    )
