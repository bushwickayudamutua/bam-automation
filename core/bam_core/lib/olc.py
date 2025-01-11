# This is a heavily reduced version of Google's Python Open Location Code
# library. Whereas the original purpose of plus codes was to act as a substitute
# for addresses, here we use it as a way to obscure exact locations. For this
# reason, we only enable 8 character encodings, as opposed to the default of 10.
#
# Example:
#
#   Encode a location:
#   encode(47.365590, 8.524997)

import math
from typing import Optional

# A separator used to break the code into two parts to aid memorability.
SEPARATOR_ = "+"

# The number of characters to place before the separator.
SEPARATOR_POSITION_ = 8

# The character set used to encode the values.
CODE_ALPHABET_ = "23456789CFGHJMPQRVWX"

# The base to use to convert numbers to/from.
ENCODING_BASE_ = len(CODE_ALPHABET_)

# The maximum value for latitude in degrees.
LATITUDE_MAX_ = 90

# The maximum value for longitude in degrees.
LONGITUDE_MAX_ = 180

# The max number of digits to process in a plus code.
MAX_DIGIT_COUNT_ = 15

# Maximum code length using lat/lng pair encoding. The area of such a
# code is approximately 13x13 meters (at the equator), and should be suitable
# for identifying buildings. This excludes prefix and separator characters.
PAIR_CODE_LENGTH_ = 10

# Inverse of the precision of the pair section of the code.
PAIR_PRECISION_ = ENCODING_BASE_**3

# Number of digits in the grid precision part of the code.
GRID_CODE_LENGTH_ = MAX_DIGIT_COUNT_ - PAIR_CODE_LENGTH_

# Number of columns in the grid refinement method.
GRID_COLUMNS_ = 4

# Number of rows in the grid refinement method.
GRID_ROWS_ = 5

# Multiply latitude by this much to make it a multiple of the finest
# precision.
FINAL_LAT_PRECISION_ = PAIR_PRECISION_ * GRID_ROWS_ ** (
    MAX_DIGIT_COUNT_ - PAIR_CODE_LENGTH_
)

# Multiply longitude by this much to make it a multiple of the finest
# precision.
FINAL_LNG_PRECISION_ = PAIR_PRECISION_ * GRID_COLUMNS_ ** (
    MAX_DIGIT_COUNT_ - PAIR_CODE_LENGTH_
)

# Length for Bushwick plus codes
BWK_CODE_LENGTH_ = 8

# Precision for latitude values
LATITUDE_PRECISION_ = pow(20, math.floor((BWK_CODE_LENGTH_ / -2) + 2))


def encode(
    latitude: Optional[float], longitude: Optional[float]
) -> Optional[str]:
    """
    Encode a location into an Open Location Code.
    Produces a code of length BWK_CODE_LENGTH_ = 8.
    Args:
    latitude: A latitude in signed decimal degrees. Will be clipped to the
        range -90 to 90.
    longitude: A longitude in signed decimal degrees. Will be normalized to
        the range -180 to 180.
    """
    if not latitude or not longitude:
        return None
    # Ensure that latitude and longitude are valid.
    latitude = clip_latitude(latitude)
    longitude = normalize_longitude(longitude)
    # Latitude 90 needs to be adjusted to be just less, so the returned code
    # can also be decoded.
    if latitude == 90:
        latitude = latitude - LATITUDE_PRECISION_
    code = ""

    # Compute the code.
    # This approach converts each value to an integer after multiplying it by
    # the final precision. This allows us to use only integer operations, so
    # avoiding any accumulation of floating point representation errors.

    # Multiply values by their precision and convert to positive.
    # Force to integers so the division operations will have integer results.
    # Note: Python requires rounding before truncating to ensure precision!
    latVal = int(round((latitude + LATITUDE_MAX_) * FINAL_LAT_PRECISION_, 6))
    lngVal = int(round((longitude + LONGITUDE_MAX_) * FINAL_LNG_PRECISION_, 6))
    latVal //= pow(GRID_ROWS_, GRID_CODE_LENGTH_)
    lngVal //= pow(GRID_COLUMNS_, GRID_CODE_LENGTH_)
    # Compute the pair section of the code.
    for i in range(0, PAIR_CODE_LENGTH_ // 2):
        code = CODE_ALPHABET_[lngVal % ENCODING_BASE_] + code
        code = CODE_ALPHABET_[latVal % ENCODING_BASE_] + code
        latVal //= ENCODING_BASE_
        lngVal //= ENCODING_BASE_

    # Add the separator character.
    code = code[:SEPARATOR_POSITION_] + SEPARATOR_ + code[SEPARATOR_POSITION_:]

    # Return the truncated section.
    return code[0 : BWK_CODE_LENGTH_ + 1]


def clip_latitude(latitude):
    """
    Clip a latitude into the range -90 to 90.
    Args:
        latitude: A latitude in signed decimal degrees.
    """
    return min(90, max(-90, latitude))


def normalize_longitude(longitude):
    """
    Normalize a longitude into the range -180 to 180, not including 180.
    Args:
    longitude: A longitude in signed decimal degrees.
    """
    while longitude < -180:
        longitude = longitude + 360
    while longitude >= 180:
        longitude = longitude - 360
    return longitude
