import numpy as np
from hand import Hand

import lyrics


if __name__ == "__main__":
    hand = Hand()

    # usage demo
    lines = [
        "zeroTier adalah perangkat lunak yang memungkinkan pembentukan",
        "jaringan pribadi virtual (VPN) secara aman dan mudah diatur.",
        "Dikembangkan oleh zeroTier, Inc., perangkat lunak ini menggunakan",
        "teknologi jaringan peer-to-peer (P2P) untuk memungkinkan koneksi",
        "langsung antar perangkat tanpa harus melewati server perantara. Hal ini",
        "mengurangi latensi dan meningkatkan kecepatan data, sehingga",
        "memungkinkan komunikasi yang efisien dan stabil, meskipun terjadi",
        "perubahan alamat IP atau topologi jaringan. zeroTier juga menciptakan",
        "Virtual Local Area Network (VLAN) yang memungkinkan perangkat di",
        "berbagai lokasi geografis untuk terhubung seolah-olah berada dalam satu",
        "jaringan lokal, sehingga memudahkan berbagi sumber daya seperti file",
        "dan aplikasi. Keamanan menjadi salah satu keunggulan utama zeroTier.",
        "Dengan implementasi enkripsi end-to-end menggunakan protokol AES-256,",
        "zeroTier memastikan bahwa data yang ditransmisikan tetap aman dari",
        "penyadapan dan akses yang tidak sah. Di samping itu, zeroTier dirancang",
        "untuk skalabilitas yang tinggi, memungkinkan ribuan perangkat terhubung",
        "dalam satu jaringan tanpa mengurangi performa. Fleksibilitasnya juga",
        "tercermin dari dukungan multi-platform, mulai dari Windows, macOS,",
        "Linux, hingga perangkat mobile seperti iOS dan Android. Selain",
        "kemudahan dalam konfigurasi dan manajemen melalui konsol web,",
        "zeroTier menawarkan berbagai aplikasi yang luas, termasuk remote",
        "access, penghubung perangkat Internet of Things (IoT), jaringan",
        "permainan multiplayer dengan latensi rendah, serta kolaborasi tim di",
        "berbagai lokasi. Dibandingkan dengan VPN tradisional seperti OpenVPN",
        "atau IPsec, zeroTier unggul dalam hal kemudahan penggunaan, kinerja",
        "yang lebih cepat karena koneksi P2P, serta fleksibilitas dalam",
        "mendukung jaringan yang lebih besar dan beragam. Dengan teknologi",
        "yang inovatif, zeroTier menjadi solusi VPN yang kuat dan andal bagi",
        "individu maupun organisasi yang memerlukan jaringan pribadi yang aman",
        "dan efisien.",
    ]
    biases = [2.5 for i in lines]
    styles = [3 for i in lines]
    stroke_widths = [1 for i in lines]

    hand.write(
        filename="nyoba.svg",
        lines=lines,
        biases=biases,
        styles=styles,
        stroke_widths=stroke_widths,
    )
