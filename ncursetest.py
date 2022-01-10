import sys,os
import curses

# limits output to maximum width
def limit(length: int, string: str):
    if len(string) > length:
        return string[:length]
    else:
        return string

def draw(stdscr):
    pressed_key = 0
    cursor_x = 0
    cursor_y = 0

    # invis cursor
    curses.curs_set(0)

    stdscr.clear()
    stdscr.refresh()

    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # create menu
    menu = ["Run", "Help", "Memory", "Settings", "Exit"]
    menu_color = curses.color_pair(3)
    menu_highlight_color = curses.color_pair(2)

    while (pressed_key != ord('q')):

        stdscr.erase()
        height, width = stdscr.getmaxyx()

        # check if height or width is too small
        if height < 20 or width < 20:
            whstr = "Terminal too small, duh!"
            import time
            while height < 20 or width < 20:
                height, width = stdscr.getmaxyx()
                stdscr.erase()
                stdscr.addstr(0, 0, limit(width, whstr), curses.color_pair(2))
                stdscr.refresh()
                time.sleep(0.1)

        # apply movement of cursor
        if pressed_key == curses.KEY_DOWN:
            cursor_y = cursor_y + 1
        elif pressed_key == curses.KEY_UP:
            cursor_y = cursor_y - 1
        elif pressed_key == curses.KEY_RIGHT:
            cursor_x = cursor_x + 1 
        elif pressed_key == curses.KEY_LEFT:
            cursor_x = cursor_x - 1

        # check if cursor is out of bounds
        cursor_x = min(cursor_x, len(menu) - 1)
        cursor_x = max(0, cursor_x)
        cursor_y = max(0, cursor_y)
        cursor_y = min(cursor_y, len(menu) - 1)

        # iterate through menu
        stdscr.attron(menu_color)
        length = 0
        for i in range(len(menu)):
            if i == cursor_x:
                stdscr.attron(menu_highlight_color)
            stdscr.addstr(height-1-height+1, length, menu[i])
            length += len(menu[i]) + 2
            stdscr.attroff(menu_highlight_color)
            stdscr.attron(menu_color)
        stdscr.attroff(menu_color)

        # render title
        stdscr.attron(curses.color_pair(2))
        stdscr.attron(curses.A_BOLD)
        title = "Curses Demo"[:width-1]
        start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
        start_y_title = int((height // 2) - 2)
        stdscr.addstr(start_y_title, start_x_title, title)
        stdscr.attroff(curses.color_pair(2))
        stdscr.attroff(curses.A_BOLD)

        # render status bar
        stdscr.attron(curses.color_pair(4))
        statusbarstr = "Nothing Selected"
        if pressed_key == 10:
            statusbarstr = menu[cursor_y] + " Selected"
        stdscr.addstr(height-1, 0, statusbarstr)
        stdscr.addstr(height-1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
        stdscr.attroff(curses.color_pair(3))

        # move cursor
        # stdscr.move(cursor_y, cursor_x)

        # Refresh the screen
        stdscr.refresh()

        # Wait for next input
        pressed_key = stdscr.getch()

def main():
    curses.wrapper(draw)

if __name__ == "__main__":
    main()
