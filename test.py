import imageio
imageio.plugins.ffmpeg.download()

from moviepy.editor import *

main_vid = "quinny.mov"
trimmed_name = main_vid[0:-4]

my_clip = VideoFileClip(main_vid)

#my_new_clip = my_clip.subclip(t_start=0, t_end=12)

#my_new_clip.write_videofile("quinny_clip_3.mov", codec="mpeg4")

all_clips = [(0, 3), (4, 7), (5, 15)]

for i in range(len(all_clips)):
    clip = all_clips[i]
    clip_name = trimmed_name + "_clip_" + str(i) + ".mov"
    new_clip = my_clip.subclip(t_start=clip[0], t_end=clip[1])
    new_clip.write_videofile(clip_name, codec="mpeg4")
