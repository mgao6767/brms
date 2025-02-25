"""BRMS - Bank Risk Management Simulation.

BRMS is an educational tool designed to provide users with an in-depth understanding of bank risk management practices.
It allows users to simulate and respond to various risk scenarios, and analyze the impact on a bank's financial health.

BRMS generally follows the Model-View-Controller (MVC) design pattern for maintainability.
Additional modules are to implement core functionalities that are independent of the GUI.
"""

import importlib.metadata
import os

DEBUG_MODE = os.getenv("BRMS_DEBUG", "False").lower() == "true"

__version__ = importlib.metadata.version("brms")
__author__ = "Mingze Gao"
__email__ = "adrian.gao@outlook.com"
__github__ = "https://github.com/mgao6767/brms"
__homepage__ = "https://bankrisk.org"

__about__ = f"""
<p><strong>BRMS - Bank Risk Management Simulation</strong> v{__version__}</p>

<p>BRMS is developed by Dr. <a href="https://mingze-gao.com">Mingze Gao</a> 
from the Department of Applied Finance at 
<a href="https://www.mq.edu.au/macquarie-business-school">
Macquarie Business School</a>.</p>

<p>BRMS is an educational tool designed to provide users with an in-depth 
understanding of bank risk management practices. It allows users to 
simulate and respond to various risk scenarios, and analyze the impact on 
a bank's financial health.</p>

<p>This application is for educational purposes only and not a substitute 
for professional risk management advice. No liability is assumed for its use. 
BRMS is licensed under the MIT License.</p>

<p>For more information, please contact the developer at 
<a href="mailto:mingze.gao@mq.edu.au">mingze.gao@mq.edu.au</a>.</p>
"""
