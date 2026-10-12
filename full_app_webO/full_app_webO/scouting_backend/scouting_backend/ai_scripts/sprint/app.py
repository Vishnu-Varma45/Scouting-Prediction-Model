from analyzer import analyze_video
from report import save_report

result = analyze_video(
    "videos/sprint.mp4"
)

save_report(result)

print(result)