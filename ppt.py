from pptx import Presentation
from pptx.util import Inches, Pt

import re

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


FULL_TEXT = open('static/temp/Test-File.txt').readlines()


# def find_text_by_time(start_clip, end_clip, source):

def find_text_by_time(source):
    """Pulls corresponding text based on clip"""

    start_time = '00:08:5\d.\d{3}'
    end_time = '00:09:1\d.\d{3}'

    start_search = re.search(start_time, source)
    end_search = re.search(end_time, source)

    print start_search.group(0), end_search.group(0)


def find_text_by_page_line(start_pl, end_pl, source):
    """Pulls text based on page and line numbers"""

    start_page_line = start_pl.split(':')
    end_page_line = end_pl.split(':')

    # start_page = re.compile('0%s:\d{2}' % start_page_line[0])
    
    # for line in FULL_TEXT:
    #     result = re.search('0%s:\d{2}' % start_page_line[0], line)
    #     if result is not None:
    #         if start_page_line[1] is not '01':

    start_pos = 0
    for i in range(len(FULL_TEXT)):
        result = re.search('0%s:\d{2}' % start_page_line[0], FULL_TEXT[i])
        if result is not None:
            start_line = int(start_page_line[1])
            if start_line > 1:
                start_pos = i + start_line - 1
                break

    print start_pos

    # start_page_line = start_pl.split(':')
    # end_page_line = end_pl.split(':')

    # start_page = re.compile('0%s:\d{2}' % start_page_line[0])
    # start_search = start_page.finditer(source)

    # start_page_ind = 0
    # # get the index of the page number
    # for s in start_search:
    #     start_page_ind = s.start()

    # end_page = re.compile('0%s:\d{2}' % start_page_line[0])
    # end_search = end_page.finditer(source)

    # end_page_ind = 0
    # # get the index of the page number
    # for e in end_search:
    #     end_page_ind = e.start()

    # line_nums = re.compile('(\d\d\d:|\s\s\s)({})(\s\s)'.format(start_page_line[1]))
    # line_search = line_nums.finditer(source, start_page_ind, end_page_ind)

    # timecode = re.compile("\d{2}:\d{2}:\d{2}.\d{3}")


    # find the page num in the text
    # look for the page followed by a colon and 2 nums
    # spl_search = '0'+start_page_line[0]+':\d{2}'
    # start_search = re.search(spl_search, source)

    print start_page

regobj = find_text_by_page_line('13:16', '14:08', FULL_TEXT)