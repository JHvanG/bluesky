''' BlueSky command-line argument parsing. '''
import argparse
from bluesky import settings


def parse():
    parser = argparse.ArgumentParser(prog="BlueSky", description="   *****   BlueSky Open ATM simulator *****")

    def setmodegui(mode, gui=None, discoverable=None, detached=None):
        class ModeGuiAction(argparse.Action):
            def __call__(self, parser, namespace, values=None, option_string=''):
                namespace.mode = mode
                namespace.gui = gui
                namespace.hostname = values or None
                if discoverable is not None:
                    namespace.discoverable = discoverable
                if detached is not None:
                    namespace.detached = detached

        return ModeGuiAction


    # Add all possible arguments to bluesky here
    mode = parser.add_mutually_exclusive_group()
    mode.set_defaults(mode="server", gui="qtgl", hostname=None, detached=False)
    mode.add_argument("--headless", dest="mode", action=setmodegui("server", discoverable=True), nargs=0, help="Start simulation server only, without GUI.")
    mode.add_argument("--client", dest="hostname", action=setmodegui("client", "qtgl"),
                    nargs="?", default=None, help="Start QtGL graphical client, which can connect to an already running server. When no hostname is passed, a discovery dialog is shown to let the user select a BlueSky server")
    mode.add_argument("--console", dest="hostname", action=setmodegui("client", "console"),
                    nargs="?", default=None, help="Start console client, which can connect to an already running server. When no hostname is passed, a discovery dialog is shown to let the user select a BlueSky server")
    mode.add_argument("--sim", dest="mode", action=setmodegui("sim"),
                    nargs=0, help="Start only one simulation node.")
    mode.add_argument("--detached", dest="mode", action=setmodegui("sim", detached=True),
                    nargs=0, help="Start only one simulation node, without networking.")


    parser.add_argument("--configfile", dest="configfile",
                        help="Load an alternative configuration file.")

    scnparse = parser.add_mutually_exclusive_group()
    scnparse.add_argument(dest="scenfile", nargs="?", default=argparse.SUPPRESS,
                        help="Load scenario file on startup.")
    scnparse.add_argument("--scenfile", dest="scenfile",
                        help="Load scenario file on startup.")

    parser.add_argument("--discoverable", dest="discoverable", action="store_const", const=True,
                        default=False, help="Make simulation server discoverable. (Default in headless mode).")
    
    parser.add_argument("--workdir", dest="workdir",
                        help="Set BlueSky working directory (if other than cwd or ~/bluesky).")

    parser.add_argument("--approaches", type=int, choices=[2, 3], dest="approaches", help="Define number of approaches (2 or 3)")
    parser.add_argument("--reward", type=str, choices=["CPA", "LNAV", "SPARSE"], dest="reward", help="Define reward function (CPA, LNAV or SPARSE)")
    parser.add_argument("--batch", type=int, choices=[32, 64, 128], dest="batch", help="Define batch size")
    parser.add_argument("--buffer", type=int, choices=[1000, 10000, 100000, 1000000], dest="buffer", help="Define buffer size")
    parser.add_argument("--lr", type=float, choices=[0.01, 0.001, 0.0001, 0.00001], default=0.0001, dest="lr", help="Define learning rate")

    cmdargs = parser.parse_args()

    return vars(cmdargs)
