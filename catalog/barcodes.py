import base64
from html import escape


class BarcodeValueError(ValueError):
    pass


CODE128_PATTERNS = [
    '212222',
    '222122',
    '222221',
    '121223',
    '121322',
    '131222',
    '122213',
    '122312',
    '132212',
    '221213',
    '221312',
    '231212',
    '112232',
    '122132',
    '122231',
    '113222',
    '123122',
    '123221',
    '223211',
    '221132',
    '221231',
    '213212',
    '223112',
    '312131',
    '311222',
    '321122',
    '321221',
    '312212',
    '322112',
    '322211',
    '212123',
    '212321',
    '232121',
    '111323',
    '131123',
    '131321',
    '112313',
    '132113',
    '132311',
    '211313',
    '231113',
    '231311',
    '112133',
    '112331',
    '132131',
    '113123',
    '113321',
    '133121',
    '313121',
    '211331',
    '231131',
    '213113',
    '213311',
    '213131',
    '311123',
    '311321',
    '331121',
    '312113',
    '312311',
    '332111',
    '314111',
    '221411',
    '431111',
    '111224',
    '111422',
    '121124',
    '121421',
    '141122',
    '141221',
    '112214',
    '112412',
    '122114',
    '122411',
    '142112',
    '142211',
    '241211',
    '221114',
    '413111',
    '241112',
    '134111',
    '111242',
    '121142',
    '121241',
    '114212',
    '124112',
    '124211',
    '411212',
    '421112',
    '421211',
    '212141',
    '214121',
    '412121',
    '111143',
    '111341',
    '131141',
    '114113',
    '114311',
    '411113',
    '411311',
    '113141',
    '114131',
    '311141',
    '411131',
    '211412',
    '211214',
    '211232',
    '2331112',
]

START_CODE_B = 104
STOP_CODE = 106


def encode_code128_b(value):
    normalized = str(value).strip()
    if not normalized:
        raise BarcodeValueError('Введите номер штрихкода.')

    unsupported = sorted({char for char in normalized if not 32 <= ord(char) <= 126})
    if unsupported:
        raise BarcodeValueError(
            'Штрихкод может содержать только цифры, латиницу и стандартные символы.'
        )

    codes = [START_CODE_B]
    codes.extend(ord(char) - 32 for char in normalized)
    checksum = (
        START_CODE_B
        + sum(index * code for index, code in enumerate(codes[1:], start=1))
    ) % 103
    return [*codes, checksum, STOP_CODE]


def barcode_svg(value, module_width=2, bar_height=72, font_size=14):
    normalized = str(value).strip()
    codes = encode_code128_b(normalized)
    quiet_zone = 10
    text_height = font_size + 12
    units = quiet_zone * 2 + sum(
        sum(int(width) for width in CODE128_PATTERNS[code])
        for code in codes
    )
    image_width = units * module_width
    image_height = bar_height + text_height
    x = quiet_zone * module_width
    bars = []

    for code in codes:
        pattern = CODE128_PATTERNS[code]
        for index, width in enumerate(pattern):
            segment_width = int(width) * module_width
            if index % 2 == 0:
                bars.append(
                    f'<rect x="{x}" y="0" width="{segment_width}" '
                    f'height="{bar_height}" fill="#111"/>'
                )
            x += segment_width

    safe_value = escape(normalized)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{image_width}" '
        f'height="{image_height}" viewBox="0 0 {image_width} {image_height}" '
        f'role="img" aria-label="Barcode {safe_value}">'
        f'<rect width="100%" height="100%" fill="#fff"/>'
        f'{"".join(bars)}'
        f'<text x="50%" y="{bar_height + font_size + 4}" '
        f'text-anchor="middle" font-family="ui-monospace, monospace" '
        f'font-size="{font_size}" fill="#111">{safe_value}</text>'
        f'</svg>'
    )


def barcode_svg_data_uri(value, **kwargs):
    svg = barcode_svg(value, **kwargs)
    encoded = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{encoded}'
