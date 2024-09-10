import numpy as np
from hand import Hand

import lyrics


if __name__ == '__main__':
    hand = Hand()

    # usage demo
    lines = [
        "Melaprak dasar sistem tenaga listrik dengan 3d printer",
        "akwokawokwakaowaowkowakowakowakowakowako",
        "nyoba optimization pass is not enabled",
        "random bullshit random bullshit random bullshit random",
        "nyoba awjoijaoiwa pass is not enabled",
        "nyoba flkasjfdkasdjf pass is not enabled",
        "nyoba dikatakanlah pass is not enabled"
    ]
    biases = [1 for i in lines]
    styles = [7 for i in lines]
    stroke_widths = [1 for i in lines]

    hand.write(
        filename='nyoba.svg',
        lines=lines,
        biases=biases,
        styles=styles,
        stroke_widths=stroke_widths
    )