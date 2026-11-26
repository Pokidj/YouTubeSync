"""Validated transport commands and playback data, never credentials or URLs."""

import json
import math


def number(value, minimum, maximum):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError("Invalid playback value")
    return value


def command(action, value=None):
    if action in {"play", "pause"}:
        if value is not None:
            raise ValueError("Unexpected playback value")
    elif action == "seek":
        value = number(value, 0, 31 * 86400)
    elif action == "relative":
        value = number(value, -60, 60)
    elif action == "volume":
        value = number(value, 0, 100)
    elif action in {"mute", "captions"}:
        if type(value) is not bool:
            raise ValueError("Invalid mute value")
    else:
        raise ValueError("Unsupported playback command")
    return {"action": action, "value": value}


def telemetry(value):
    if not isinstance(value, dict):
        raise ValueError("Invalid playback data")
    result = {key: number(value.get(key), low, high) for key, low, high in
              (("position", 0, 31 * 86400), ("duration", 0, 31 * 86400), ("volume", 0, 100))}
    for key in ("playing", "muted"):
        if type(value.get(key)) is not bool:
            raise ValueError("Invalid playback state")
        result[key] = value[key]
    return result


def player_operation(action, value=None):
    data = command(action, value)
    action, value = data["action"], json.dumps(data["value"])
    expressions = {"play": "p.playVideo()", "pause": "p.pauseVideo()",
                   "seek": f"p.seekTo({value},true)",
                   "relative": f"p.seekTo(Math.max(0,p.getCurrentTime()+{value}),true)",
                   "volume": f"p.setVolume({value})", "mute": f"({value}?p.mute():p.unMute())",
                   "captions": "(()=>{const wanted=" + value + ";const current=typeof p.isSubtitlesOn==='function'?p.isSubtitlesOn():null;"
                   "if(typeof current==='boolean'&&typeof p.toggleSubtitles==='function'){if(current!==wanted)p.toggleSubtitles();return;}"
                   "const loaded=(p.getOptions?.()||[]).includes('captions');if(wanted&&!loaded)p.loadModule?.('captions');"
                   "else if(!wanted)p.unloadModule?.('captions');})()"}
    return expressions[action]


def iframe_command(action, value=None):
    operation = player_operation(action, value)
    if action == "captions":
        operation = "window.captionsWanted=" + json.dumps(value) + ";" + operation
    return "(()=>{const p=window.player;if(p){" + operation + ";}})()"
