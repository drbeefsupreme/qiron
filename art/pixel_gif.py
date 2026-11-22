from PIL import GifImagePlugin


def write_loop(path, frame):
    with path.open("wb") as gif:
        head,_ = GifImagePlugin.getheader(frame(0), info={"loop":0, "background":0})
        gif.writelines(head)
        previous, duration = None, 0
        for i in range(100):
            current = frame(i)
            if previous is not None and current.tobytes() != previous.tobytes():
                gif.writelines(GifImagePlugin.getdata(previous, duration=duration, disposal=2, transparency=0))
                duration = 0
            previous = current
            duration += 100
        gif.writelines(GifImagePlugin.getdata(previous, duration=duration, disposal=2, transparency=0))
        gif.write(b";")
