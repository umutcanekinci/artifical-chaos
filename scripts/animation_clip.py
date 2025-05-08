class AnimationClip:
    def __init__(self, name, duration, frame_rate):
        self.name = name
        self.duration = duration
        self.frame_rate = frame_rate
        self.frames = []

    def load_frames(self, frame_data):
        for frame in frame_data:
            self.frames.append(frame)

    def __getitem__(self, index):
        if 0 <= index < len(self.frames):
            return self.frames[index]
        else:
            raise IndexError("Frame index out of range")

    def __iter__(self):
        return iter(self.frames)

    def __len__(self):
        return len(self.frames)

    def add_frame(self, frame):
        self.frames.append(frame)

    def get_frame(self, index):
        if 0 <= index < len(self.frames):
            return self.frames[index]
        else:
            raise IndexError("Frame index out of range")

    def __repr__(self):
        return f"AnimationClip(name={self.name}, duration={self.duration}, frame_rate={self.frame_rate}, frames={len(self.frames)})"