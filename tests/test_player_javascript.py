from html.parser import HTMLParser
import json
import shutil
import subprocess
import unittest

import test_layout
from youtube_sync_youtube_player import player_html
from youtube_sync_first_party_player import media_expression

VIDEO = "aB3_cD6-eF9"


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inline = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inline = not dict(attrs).get("src")

    def handle_endtag(self, tag):
        if tag == "script":
            self.inline = False

    def handle_data(self, data):
        if self.inline:
            self.parts.append(data)


@unittest.skipUnless(shutil.which("node"), "Node required for JavaScript behavior tests")
class PlayerJavaScriptTests(unittest.TestCase):
    def run_js(self, source):
        subprocess.run([shutil.which("node"), "-e", source], check=True, capture_output=True, timeout=15)

    def test_iframe_hides_controls_disables_initial_captions_and_allows_opt_in(self):
        parser = Scripts()
        parser.feed(player_html(VIDEO, custom_controls=True, captions_off=True))
        self.run_js("""
          const assert=require('node:assert/strict');global.window=global;
          global.setInterval=()=>{};window.addEventListener=()=>{};
          let loaded=true,options;
          const p={getOptions:()=>loaded?['captions']:[],unloadModule:()=>{loaded=false},loadModule:()=>{loaded=true}};
          global.YT={Player:function(_,o){options=o;return p}};
        """ + "\n".join(parser.parts) + """
          onYouTubeIframeAPIReady();options.events.onReady({target:p});
          assert.equal(options.playerVars.controls,0);assert.equal(loaded,false);
          applyCommand({action:'captions',value:true});options.events.onApiChange();
          assert.equal(loaded,true);
          applyCommand({action:'captions',value:false});assert.equal(loaded,false);
        """)

    def test_authenticated_player_caption_policy_does_not_break_media_or_ads(self):
        expression = media_expression(VIDEO, captions=False)
        self.run_js("""
          const assert=require('node:assert/strict');global.location={origin:'https://www.youtube.com',pathname:'/embed/""" + VIDEO + """'};
          let captions=true,ad=false;
          const p={classList:{contains:()=>ad},getVideoData:()=>({video_id:'""" + VIDEO + """'}),
          getCurrentTime:()=>20,getDuration:()=>100,getVolume:()=>60,isMuted:()=>false,getPlayerState:()=>1,seekTo:()=>{},
          isSubtitlesOn:()=>captions,toggleSubtitles:()=>{captions=!captions}};
          global.document={querySelector:s=>s==='#movie_player'?p:s==='video'?{readyState:3}:null};
        """ + "const expression=" + json.dumps(expression) + ";" + """
          assert.equal(eval(expression).media,true);assert.equal(captions,false);
          captions=true;ad=true;assert.equal(eval(expression).advertising,true);assert.equal(captions,true);
        """)
