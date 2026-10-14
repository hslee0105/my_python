"""UserScenarioCLI.exe (콘솔) 진입점.

  UserScenarioCLI.exe [옵션...]                 python -m user_scenario 와 동일
  UserScenarioCLI.exe fan-analysis <결과폴더>     python -m user_scenario.fan_analysis
  UserScenarioCLI.exe tfmonitor --dump|--read   python -m user_scenario.tfmonitor
"""

import sys


def main() -> int:
    from user_scenario.utils import setup_console_encoding

    setup_console_encoding()
    argv = sys.argv[1:]
    if argv[:1] == ["fan-analysis"]:
        from user_scenario.fan_analysis import main as fan_main
        return fan_main(argv[1:])
    if argv[:1] == ["tfmonitor"]:
        from user_scenario.tfmonitor import main as tf_main
        return tf_main(argv[1:])
    from user_scenario.__main__ import main as cli_main
    return cli_main(argv)


if __name__ == "__main__":
    sys.exit(main())
