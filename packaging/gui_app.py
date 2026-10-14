"""UserScenario.exe (GUI, 콘솔 창 없음) 진입점.

  UserScenario.exe              GUI 실행
  UserScenario.exe --selftest   GUI 생성/종료만 하고 exit 0 (빌드 검증용)
"""

import sys


def main() -> int:
    from user_scenario.gui import ControllerApp, main as gui_main

    if "--selftest" in sys.argv[1:]:
        app = ControllerApp()
        app.update()
        app.destroy()
        return 0
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
