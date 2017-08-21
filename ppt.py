from pptx import Presentation
from pptx.util import Inches, Pt

# set horizontal and vertical position
vid_VP = Inches(1.91)
vid_HP = Inches(.41)

# set video width and height
vid_H = Pt(240)
vid_W = Pt(320)

def create_slide_deck(template, clips, txt_source):
    prs = Presentation(template)

    # make a new slide for each clip
    for clip in clips:
        # select the depo slide layout
        slide = prs.slides.add_slide(prs.slide_layouts[7])

        # add a video to the slide using the provided dimensions
        video = slide.shapes.add_movie(clip, vid_HP, vid_VP, vid_W, vid_H)

        print video.name, video.height

        # target the text frame on the slide
        txt = slide.placeholders[1]

        if txt.has_text_frame:
            txt.text_frame.text = txt_source

    prs.save('new-slide-deck.pptx')

clips = ['nemo2.mov', 'nemo.mov', 'nemo2.mov']
txt_source = open('sample_qa.txt').read()