from const import box_width, num_lines, char_widths, approximate_word_length, font_width, valid_char_set

def replace_invalid_chars(word, valid_char_set):
    new_word = []
    for char in word:
        if char not in valid_char_set:
            if char.lower() in valid_char_set:
                new_word.append(char.lower())
                print(f"Warning: word '{word}' is replaced by '{''.join(new_word)}' because of invalid character '{char}'")
            elif char.upper() in valid_char_set:
                new_word.append(char.upper())
                print(f"Warning: word '{word}' is replaced by '{''.join(new_word)}' because of invalid character '{char}'")
            else:
                print(f"Error: word '{word}' contains invalid character '{char}' and cannot be replaced.")
                return None
        else:
            new_word.append(char)
    return ''.join(new_word)

def segment_string_block(string_block, box_width, num_lines, char_widths, valid_char_set):
    words = string_block.split()
    lines = []
    line_lengths = []
    current_line = ""

    for word in words:
        valid_word = replace_invalid_chars(word, valid_char_set)
        if valid_word is None:
            continue

        word_length = approximate_word_length(valid_word, font_width, char_widths)
        current_line_length = approximate_word_length(current_line, font_width, char_widths)

        if current_line_length + word_length <= box_width:
            if current_line:
                current_line += " " + valid_word
            else:
                current_line = valid_word
        else:
            lines.append(current_line)
            line_lengths.append(current_line_length)
            current_line = valid_word

            if len(lines) >= num_lines:
                print("Warning: Exceeded the maximum number of lines.")
                print("Remaining unfitted words:", " ".join(words[words.index(word):]))
                return lines, line_lengths

    if current_line:
        lines.append(current_line)
        line_lengths.append(approximate_word_length(current_line, font_width, char_widths))

    return lines, line_lengths

string_block = """
ZeroTier adalah perangkat lunak yang memungkinkan pembentukan jaringan pribadi virtual (VPN) secara aman dan mudah diatur. Dikembangkan oleh ZeroTier, Inc., perangkat lunak ini menggunakan teknologi jaringan peer-to-peer (P2P) untuk memungkinkan koneksi langsung antar perangkat tanpa harus melewati server perantara. Hal ini mengurangi latensi dan meningkatkan kecepatan data, sehingga memungkinkan komunikasi yang efisien dan stabil, meskipun terjadi perubahan alamat IP atau topologi jaringan. ZeroTier juga menciptakan Virtual Local Area Network (VLAN) yang memungkinkan perangkat di berbagai lokasi geografis untuk terhubung seolah-olah berada dalam satu jaringan lokal, sehingga memudahkan berbagi sumber daya seperti file dan aplikasi.

Keamanan menjadi salah satu keunggulan utama ZeroTier. Dengan implementasi enkripsi end-to-end menggunakan protokol AES-256, ZeroTier memastikan bahwa data yang ditransmisikan tetap aman dari penyadapan dan akses yang tidak sah. Di samping itu, ZeroTier dirancang untuk skalabilitas yang tinggi, memungkinkan ribuan perangkat terhubung dalam satu jaringan tanpa mengurangi performa. Fleksibilitasnya juga tercermin dari dukungan multi-platform, mulai dari Windows, macOS, Linux, hingga perangkat mobile seperti iOS dan Android.

Selain kemudahan dalam konfigurasi dan manajemen melalui konsol web, ZeroTier menawarkan berbagai aplikasi yang luas, termasuk remote access, penghubung perangkat Internet of Things (IoT), jaringan permainan multiplayer dengan latensi rendah, serta kolaborasi tim di berbagai lokasi. Dibandingkan dengan VPN tradisional seperti OpenVPN atau IPsec, ZeroTier unggul dalam hal kemudahan penggunaan, kinerja yang lebih cepat karena koneksi P2P, serta fleksibilitas dalam mendukung jaringan yang lebih besar dan beragam. Dengan teknologi yang inovatif, ZeroTier menjadi solusi VPN yang kuat dan andal bagi individu maupun organisasi yang memerlukan jaringan pribadi yang aman dan efisien.
"""

# Segment the string_block into lines
segmented_lines, line_lengths = segment_string_block(string_block, box_width, num_lines, char_widths, valid_char_set)

# Output the lines and their lengths
print("lines = [")
for line in segmented_lines:
    print(f"  \"{line}\",")
print("]")

print("line length = [")
for length in line_lengths:
    print(f"  {length},")
print("]")
print("box_width =", box_width)
print("Total number of lines:", len(segmented_lines))