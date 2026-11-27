import json, os, subprocess, time
from pathlib import Path
from PIL import Image

FFMPEG=os.environ.get("STORY_FFMPEG",str(Path.home()/"ai/tools/media/bin/ffmpeg"))
FFPROBE=os.environ.get("STORY_FFPROBE",str(Path.home()/"ai/tools/media/bin/ffprobe"))
PROFILE=os.environ.get("STORY_PROFILE","flux")
AUDIO_GAIN=float(os.environ.get("STORY_AUDIO_GAIN","0.85"))


def encode(paths:list[Path],segments:list[tuple[int,int,int]],size:tuple[int,int],f:int,n:int,audio:Path,out:Path,*,episode=False)->dict:
    started=time.monotonic()
    if not 0<AUDIO_GAIN<=1:
        raise ValueError("STORY_AUDIO_GAIN must be in (0,1]")
    w,h=size
    if not segments or segments[0][0] != 0 or segments[-1][1] != n or any(a >= b for a, b, _ in segments):
        raise ValueError("timeline does not cover the encoded frame range")
    if any(left[1] != right[0] for left, right in zip(segments, segments[1:])):
        raise ValueError("timeline segments are not contiguous")
    end=n/f
    def exceeds_limit(duration):
        return duration > 300 if episode else duration >= 45
    limit = "300-second episode maximum" if episode else "strictly below 45 seconds"
    if exceeds_limit(end):raise ValueError(f"rounded encoded duration must be {limit}")
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{w}x{h}",
         "-framerate",str(f),"-i","pipe:0","-i",str(audio),"-filter:a",f"volume={AUDIO_GAIN},apad",
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-r",str(f),
         "-c:a","aac","-b:a","160k","-ar","48000","-t",f"{end:.9f}","-frames:v",str(n),"-movflags","+faststart",str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for start,stop,p in segments:
            with Image.open(paths[p]) as img:
                frame=img.convert("RGB").tobytes()
            for _ in range(start,stop):
                proc.stdin.write(frame)
        proc.stdin.close()
        error=proc.stderr.read().decode(errors="replace")
        code=proc.wait()
    except Exception:
        proc.kill();proc.wait();raise
    if code:raise RuntimeError(f"FFmpeg encode failed: {error[-1200:]}")
    info=subprocess.check_output([FFPROBE,"-v","error","-count_frames","-show_streams","-show_format","-of","json",str(out)],text=True)
    data=json.loads(info)
    streams=data["streams"]
    video=next((x for x in streams if x["codec_type"]=="video"),{})
    sound=next((x for x in streams if x["codec_type"]=="audio"),{})
    if (not video or not sound or video.get("codec_name")!="h264" or sound.get("codec_name")!="aac"
            or video.get("pix_fmt")!="yuv420p" or video.get("avg_frame_rate")!=f"{f}/1"
            or sound.get("sample_rate")!="48000"
            or video.get("width")!=w or video.get("height")!=h or int(video.get("nb_read_frames",0))!=n):
        raise RuntimeError(f"encoded stream verification failed: {video} {sound}")
    if exceeds_limit(max(float(data["format"]["duration"]),float(video.get("duration",0)),float(sound.get("duration",0)))):
        raise RuntimeError("muxed output exceeds profile limit")
    subprocess.run([FFMPEG,"-v","error","-i",str(out),"-f","null","-"],check=True,timeout=300)
    return {"expected_video_frames":n,"expected_duration":end,"audio_gain":AUDIO_GAIN,
            "assembly_seconds":round(time.monotonic()-started,3),"ffprobe":data}
