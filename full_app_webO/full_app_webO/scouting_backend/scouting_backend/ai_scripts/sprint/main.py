from analyzer import analyze_video

result = analyze_video(
    "videos/sprint.mp4"
)

for key, value in result.items():

    print(
        f"{key}: {value}"
    )