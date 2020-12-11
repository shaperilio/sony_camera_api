from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
from io import BytesIO
import time

# Wraps text so it fits within max_width.
def wrap(msg, max_width=70):
    lines = []
    words = msg.split(' ')
    line = ''
    for i in range(len(words)):
        this_word = words[i]
        if len(line + this_word + ' ') > max_width:
            # If we add this word, the line will be too long.
            # First, check if this is just a really long word.
            if len(line) == 0:
                # This word is too long for our width limit, so we force it
                line = this_word
                lines.append(line)
                line = ''
                continue
            # Line already has stuff in it. So append this line, and start
            # the next one with this word.
            lines.append(line)
            line = this_word + ' '
            continue
        # Line still has room, so add this word and go to the next word.
        line += this_word + ' '
    lines.append(line)
    return '\n'.join(lines)

def get_jpeg_for_message(msg):
    img = Image.new('RGB', (640, 480))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Menlo.ttc", 15) # mac
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 15) # windows
        except:
            font = ImageFont.truetype("DejaVuSans.ttf", 15) # ubuntu

    msg = time.strftime('%Y-%m-%d %H:%M:%S') + '\n' + wrap(msg)
    draw.text((10, 10),msg,(255,255,255),font=font)
    # BytesIO cleverness from https://stackoverflow.com/a/14921165/149506
    result = BytesIO()
    img.save(result, format='JPEG')
    return result.getvalue()