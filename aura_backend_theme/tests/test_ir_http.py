from odoo.tests.common import TransactionCase
from odoo.addons.aura_backend_theme.models.ir_http import _hex_to_rgb, _darken

class TestIrHttpTheme(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_hex_to_rgb_helper(self):
        """Test the explicit color transformer helper in ir_http."""
        self.assertEqual(_hex_to_rgb('#FF0000'), '255,0,0')
        self.assertEqual(_hex_to_rgb('#00FF00'), '0,255,0')
        self.assertEqual(_hex_to_rgb('#0000FF'), '0,0,255')
        self.assertEqual(_hex_to_rgb(None), '10,143,220') # DEFAULT_BRAND #0A8FDC

    def test_darken_helper(self):
        """Test explicit darkening of themes in ir_http."""
        brand = '#FF0000'
        darkened = _darken(brand, factor=0.5)
        # hex values should be roughly half of FF (which is 255) -> 127 = 7F
        self.assertEqual(darkened, '#7F0000')

