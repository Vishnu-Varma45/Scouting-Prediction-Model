def save_report(
    data,
    filename="outputs/report.txt"
):

    with open(filename, "w") as f:

        f.write("SPRINT ANALYSIS REPORT\n")
        f.write("=" * 50)
        f.write("\n\n")

        for key, value in data.items():

            if isinstance(value, list):

                f.write(
                    f"{key}:\n"
                )

                for item in value:
                    f.write(
                        f"  - {item}\n"
                    )

            else:

                f.write(
                    f"{key}: {value}\n"
                )

    print(
        f"Report saved to {filename}"
    )