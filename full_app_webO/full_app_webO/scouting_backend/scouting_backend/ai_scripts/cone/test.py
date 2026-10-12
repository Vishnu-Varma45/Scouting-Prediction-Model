from analyzer import analyze_video

result = analyze_video(
    "videos/sprint.mp4"
)

assert "mean_left_knee" in result

print("TEST PASSED")

