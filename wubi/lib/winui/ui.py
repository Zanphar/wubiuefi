#
# Copyright (c) 2007, 2008 Agostino Russo
#
# Written by Agostino Russo <agostino.russo@gmail.com>
#
# win32.ui is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
#
# win32.ui is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# DESCRIPTION:
# widgets and window classes wrapping win32 objects
#
# LINKS:
# Window Classes: http://msdn.microsoft.com/en-us/library/bb775491(VS.85).aspx
# Controls http://msdn.microsoft.com/en-us/library/bb775943(VS.85).aspx
#

from defs import *

__all__ = ["Window", "Application"]

#TBD use weakref in _event_handlers_
_event_handlers_ = {}

def event_dispatcher(hwnd, message, wparam, lparam):
    eh = _event_handlers_
    na = {}
    nas = set()
    handlers = set()
    for eh in [eh.get(hwnd, na), eh.get(None, na)]:
        for eh in [eh.get(message, na) , eh.get(None, na)]:
            for eh in [eh.get(wparam, na) , eh.get(None, na)]:
                handlers |= eh.get(lparam, nas)
                handlers |= eh.get(None, nas)
    for obj, handler_name in handlers:
        handler = getattr(obj, handler_name, None)
        if not callable(handler): continue
        if handler((hwnd, message, wparam, lparam)):
            return
    return windll.user32.DefWindowProcW(
        c_int(hwnd),
        c_int(message),
        c_int(wparam),
        c_int(lparam))

def event_handler(hwnd=None, message=None, wparam=None, lparam=None):
    '''
    Decorator for event handlers
    The handler must return True to stop further message processing by other handlers of the same Window
    '''
    def decorator(func):
        func._handled_event_ = (hwnd, message, wparam, lparam)
        return func
    return decorator

class BasicWindow(object):
    '''
    Wraps
    '''
    _window_class_name_ = None
    _window_class_style_ = CS_HREDRAW | CS_VREDRAW
    _window_style_ = 0
    _window_ex_style_ = 0

    def __init__(self, parent=None, x=None, y=None, width=None, height=None, text=None, application=None):
        self.parent = parent
        if application:
            self.application = application
        else:
            self.application = parent.application
        if not self.__class__._window_class_name_:
            self.__class__._window_class_name_ = self.__class__.__name__
            self._register_window()
        self._create_window(x, y, width, height, text)
        self._register_handlers()
        self.on_init()

    def _register_window(self):
        self._window_class_ = WNDCLASSEX(
                event_dispatcher,
                self._window_class_name_,
                self._window_class_style_)
        self._window_class_._atom_ = windll.user32.RegisterClassExW(byref(self._window_class_))
        if not self._window_class_._atom_:
            raise WinError()

    def _create_window(self, x=None, y=None, width=None, height=None, text=None):
        hmenu = NULL
        lpparam = NULL
        hwnd = self.parent and self.parent._hwnd or NULL
        application_hinstance = self.application._hinstance
        if x is None:
            x = CW_USEDEFAULT
        if y is None:
            y = CW_USEDEFAULT
        if width is None:
            width = CW_USEDEFAULT
        if height is None:
            height = CW_USEDEFAULT
        if not text:
            text = ""
        self._hwnd = CreateWindowEx(
            self._window_ex_style_,
            unicode(self._window_class_name_),
            unicode(text),
            self._window_style_,
            x, y, width, height,
            hwnd,
            hmenu,
            application_hinstance,
            lpparam)

    def _register_handlers(self):
        for key in dir(self):
            handler = getattr(self, key)
            handled_event = getattr(handler, "_handled_event_", None)
            if callable(handler) and handled_event:
                handled_event = list(handled_event)
                for i,subkey in enumerate(handled_event):
                    if subkey is SELF_HWND:
                        handled_event[i] = self._hwnd
                    elif subkey is PARENT_HWND:
                        handled_event[i] = self.parent._hwnd
                    elif subkey is APPLICATION_HINSTANCE:
                        handled_event[i] = self.application._hinstance
                self._add_event_handler(key , handled_event)

    def _add_event_handler(self, handler_name, handled_event):
        hwnd, message, wparam, lparam = handled_event
        eh = _event_handlers_
        eh = eh.setdefault(hwnd,{})
        eh = eh.setdefault(message,{})
        eh = eh.setdefault(wparam,{})
        handlers = eh.setdefault(lparam,set())
        handlers.add((self, handler_name))

    def on_init(self):
        pass

class Window(BasicWindow):
    _repaint_on_move_ = False

    def __init__(self, parent=None, x=None, y=None, width=None, height=None, text=None, application=None):
        BasicWindow.__init__(self, parent, x, y, width, height, text, application)

    def get_window_rect(self):
        rect = RECT()
        windll.user32.GetWindowRect(self._hwnd, byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom

    def get_client_rect(self):
        rect = RECT()
        windll.user32.GetClientRect(self._hwnd, byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom

    def move(self, x, y):
        if not windll.user32.SetWindowPos(self._hwnd, NULL, x, y, 0, 0,  SWP_NOSIZE):
        #~ if not windll.user32.MoveWindow(self._hwnd, x, y, -1, -1, self._repaint_on_move_): #repaint
            raise WinError()

    def resize(self, width, height):
        if not windll.user32.SetWindowPos(self._hwnd, NULL, 0, 0, width, height,  SWP_NOMOVE):
            raise WinError()

    def show(self):
        #http://msdn.microsoft.com/en-us/library/ms633548.aspx
        self.on_show()
        if not windll.user32.ShowWindow(self._hwnd, SW_SHOWNORMAL):
            #raise WinError()
            pass
        self.update()

    def enable(self):
        pass

    def disable(self):
        pass

    def hide(self):
        if not windll.user32.ShowWindow(self._hwnd, SW_HIDE):
            #~ raise WinError()
            pass

    def update(self):
        if not windll.user32.UpdateWindow(self._hwnd):
            raise WinError()

    def get_text(self):
        text = ""
        #~ textLength = self._send_message(WM_GETTEXTLENGTH) + 1
        #~ textBuff = ' ' * textLength
        #~ self._send_message(WM_GETTEXT, textLength, textBuff)
        #~ return textBuff[:-1]
        if not windll.user32.GetWindowTextW(self._hwnd, byref(text), nMaxCount=9999):
            raise WinError()

    def set_text(self, text):
        if not windll.user32.SetWindowTextW(self._hwnd, unicode(text)):
            raise WinError()

    def set_localized_text(self, text):
        text = gettext(text)
        self.set_text(text)

    def stop_redraw(self):
        self._send_message(WM_SETREDRAW, False, 0)
        #~ LockWindowUpdate(self._hwnd)
        #~ LockWindowUpdate(NULL)

    def start_redraw(self):
        self._send_message(WM_SETREDRAW, True, 0)

    def _send_message(self, message, wparam=0, lparam=0):
        return windll.user32.SendMessageW(self._hwnd, message, wparam, lparam)

    @event_handler(message=WM_DESTROY, hwnd=SELF_HWND)
    def _on_destroy(self, event):
        self.on_destroy()

    @event_handler(message=WM_PAINT, hwnd=SELF_HWND)
    def _on_paint(self, event):
        self.on_paint()

    def on_paint(self):
        pass

    def on_show(self):
        pass

    def on_destroy(self):
        pass

class Application(object):
    _main_window_class_ = Window

    def __init__(self, main_window_class=None, **kargs):
        self._hwnd = None
        self._hinstance = windll.kernel32.GetModuleHandleW(c_int(NULL))
        kargs["application"] = self
        if not main_window_class:
            main_window_class = self._main_window_class_
        self.main_window = main_window_class(**kargs)
        self.on_init()

    def run(self):
        self.on_run()
        self.main_window.show()
        self._pump_messages()

    def _pump_messages(self):
        msg = MSG()
        pMsg = pointer(msg)
        while windll.user32.GetMessageW(pMsg, NULL, 0, 0):
            windll.user32.TranslateMessage(pMsg)
            windll.user32.DispatchMessageW(pMsg)
        return msg.wParam

    def on_init(self):
        pass

    def on_run(self):
        pass

    def quit(self):
        windll.user32.DestroyWindow(self.main_window._hwnd)

    def on_quit(self):
        pass

    def show_error_message(self, message, title=None):
        result = windll.user32.MessageBoxW(self.main_window._hwnd, unicode(message), unicode(title), MB_OK|MB_ICONERROR)

    def show_info_message(self, message, title=None):
        result = windll.user32.MessageBoxW(self.main_window._hwnd, unicode(message), unicode(title), MB_OK|MB_ICONINFORMATION)

    def ask_confirmation(self, message, title=None):
        result = windll.user32.MessageBoxW(self.main_window._hwnd, unicode(message), unicode(title), MB_YESNO|MB_ICONQUESTION)
        return result == IDYES

    def ask_to_retry(self, message, title=None):
        result = windll.user32.MessageBoxW(self.main_window._hwnd, unicode(message), unicode(title), MB_RETRYCANCEL)
        return result == IDRETRY

class MainWindow(Window):
    '''
    Main Window
    Has borders, and is overlapped, when it is closed, the application quits
    '''

    _window_class_name_ = None
    _window_style_ = WS_OVERLAPPEDWINDOW

    def on_destroy(self):
        windll.user32.PostQuitMessage(0)
        self.application.on_quit()

    def __del__(self):
        self.application.on_quitt()

class MainDialogWindow(MainWindow):
    '''
    Like MainWindow
    But cannot be resized, looks like a dialog
    '''
    _window_style_ =  WS_BORDER |  WS_SYSMENU | WS_CAPTION

class Widget(Window):
    _window_class_name_ = "Must Override This"
    _window_style_ = WS_CHILD | WS_VISIBLE | WS_TABSTOP
    _window_ex_style_ = 0

    @event_handler(message=WM_COMMAND, lparam=SELF_HWND)
    def _on_command(self, event):
        self.on_command(event)

    def on_command(self, event):
        pass

class StaticWidget(Window):
    _window_class_name_ = "STATIC"
    _window_style_ = WS_CHILD | WS_VISIBLE

class Panel(Window):
    _window_class_name_ = None
    _window_style_ = WS_CHILD | WS_VISIBLE
    _window_ex_style_ = 0
    #_window_style_ = StaticWidget._window_style_|WS_BORDER

class Edit(Widget):
    _window_class_name_ = "EDIT"
    _window_ex_style_ = WS_EX_CLIENTEDGE

class Tab(Widget):
    #define WC_TABCONTROLW          L"SysTabControl32"   ???
    _window_class_name_ = "SysTabControl32"

    def add_item(self, title, child, position=0):
        item = TCITEM()
        item.mask = TCIF_TEXT | TCIF_PARAM
        item.pszText = unicode(title)
        item.lParam = child._hwnd
        #~ self.InsertItem(index, item)
        #~ self._ResizeChild(child)
        #~ self.SetCurrentTab(index)
        self._send_message(TCM_INSERTITEM, position, byref(item))

class Tooltip(Widget):
    _window_class_name_ = u"SysTabControl32"


class ListBox(Widget):
    _window_class_name_ = "ListBox"
    _window_style_ = Widget._window_style_

    def add_item(self, text):
        self._send_message(LB_ADDSTRING, 0, unicode(text))

class ComboBox(Widget):
    _window_class_name_ = "COMBOBOX" #"ComboBoxEx32"
    _window_style_ = Widget._window_style_ | CBS_DROPDOWNLIST | WS_VSCROLL

    def add_item(self, text):
        self._send_message(CB_ADDSTRING, 0, unicode(text))

class SortedComboBox(ComboBox):
    _window_style_ = ComboBox._window_style_ | CBS_SORT

class Button(Widget):
    _window_class_name_ = "BUTTON"
    _window_style_ = Widget._window_style_ | BS_PUSHBUTTON

    def on_command(self, event):
        if event[2] == 0:
            self.on_click()

    def is_checked(self):
        value = self._send_message(BM_GETCHECK, 0, 0)
        return value == BST_CHECKED

    def on_click(self):
        pass

class DefaultButton(Button):
    _window_style_ = Widget._window_style_ | BS_DEFPUSHBUTTON

class RadioButton(Button):
    _window_class_name_ = "BUTTON"
    _window_style_ = Widget._window_style_ | BS_AUTORADIOBUTTON

class GroupBox(Button):
    _window_class_name_ = "BUTTON"
    _window_style_ = Widget._window_style_ |BS_GROUPBOX

class CheckButton(Button):
    _window_class_name_ = "BUTTON"
    _window_style_ = Widget._window_style_ | BS_AUTOCHECKBOX

class Label(StaticWidget):
    _window_class_name_ = "Static"
    _window_style_ = StaticWidget._window_style_|SS_SIMPLE

class Bitmap(Widget):
    _window_class_name_ = "Static"
    _window_style_ = StaticWidget._window_style_|SS_BITMAP

    def set_image(self, path, width=0, height=0):
        path = unicode(path)
        himage = windll.user32.LoadImageW(NULL, path, IMAGE_BITMAP, width, height, LR_LOADFROMFILE);
        test = self._send_message(STM_SETIMAGE, IMAGE_BITMAP, himage)

    def on_destroy(self):
        pass
        #TBD Free resources
        #windll.user32.DeleteObject(himage)???

class Icon(StaticWidget):
    _window_class_name_ = "Static"
    _window_style_ = StaticWidget._window_style_|SS_ICON

class ProgressBar(Widget):
    _window_class_name_ = "msctls_progress32"

    def set_position(self, position):
        return self._send_message(PBM_SETPOS, position, 0)

    def get_position(self):
        return self._send_message(PBM_GETPOS, 0, 0)

    def set_bar_color(self, color):
        return self._send_message(PBM_SETBARCOLOR, 0, color)

    def set_background_color(self, clrBk):
        return self._send_message(PBM_SETBKCOLOR, 0, color)

    def step(self, n=1):
        step0 = self.get_position()
        #~ if not n:
            #~ step1 = self._send_message(PBM_STEPIT, 0, 0) #PBM_DELTAPOS
        step1 = self.set_position(step0 + n)
        self.on_change()
        return step1

    def on_change(self):
        pass

class Link(Widget):
    _window_class_name_ = "Link"

class Page(Window):
    _window_class_name_ = None
    _window_style_ = WS_CHILD
    _window_ex_style_ = 0
