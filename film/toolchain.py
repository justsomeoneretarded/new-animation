"""A packaged FFmpeg binary avoids slow Ubuntu mirror updates in Actions."""
from pathlib import Path
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

def check_fonts():
    root=Path('/usr/share/fonts/truetype/dejavu')
    for name in ['DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSerif.ttf','DejaVuSans-Oblique.ttf']:
        if not (root/name).is_file():
            raise RuntimeError('Install fonts-dejavu-core; missing '+str(root/name))

if __name__=='__main__':
    import subprocess
    check_fonts()
    subprocess.run([FFMPEG,'-version'],check=True)
