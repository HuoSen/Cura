from __future__ import absolute_import
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os, wx, threading, sys

from Cura.avr_isp import stk500v2
from Cura.avr_isp import ispBase
from Cura.avr_isp import intelHex

from Cura.util import machineCom
from Cura.util import profile
from Cura.util import resources

def getDefaultFirmware():
	if profile.getPreference('machine_type') == 'ultimaker':
		if profile.getPreference('has_heated_bed') == 'True':
			return None
		if profile.getPreferenceFloat('extruder_amount') > 2:
			return None
		if profile.getPreferenceFloat('extruder_amount') > 1:
			if sys.platform.startswith('linux'):
				return resources.getPathForFirmware("MarlinUltimaker-115200-dual.hex")
			else:
				return resources.getPathForFirmware("MarlinUltimaker-250000-dual.hex")
		if sys.platform.startswith('linux'):
			return resources.getPathForFirmware("MarlinUltimaker-115200.hex")
		else:
			return resources.getPathForFirmware("MarlinUltimaker-250000.hex")
	return None

class InstallFirmware(wx.Dialog):
	def __init__(self, filename = None, port = None):
		super(InstallFirmware, self).__init__(parent=None, title="固件安装", size=(250, 100))
		if port is None:
			port = profile.getPreference('serial_port')
		if filename is None:
			filename = getDefaultFirmware()
		if filename is None:
			wx.MessageBox('很抱歉，Cura没有您设备的固件。', '固件升级', wx.OK | wx.ICON_ERROR)
			self.Destroy()
			return

		sizer = wx.BoxSizer(wx.VERTICAL)
		
		self.progressLabel = wx.StaticText(self, -1, 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\nX')
		sizer.Add(self.progressLabel, 0, flag=wx.ALIGN_CENTER)
		self.progressGauge = wx.Gauge(self, -1)
		sizer.Add(self.progressGauge, 0, flag=wx.EXPAND)
		self.okButton = wx.Button(self, -1, 'Ok')
		self.okButton.Disable()
		self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
		sizer.Add(self.okButton, 0, flag=wx.ALIGN_CENTER)
		self.SetSizer(sizer)
		
		self.filename = filename
		self.port = port

		self.Layout()
		self.Fit()

		threading.Thread(target=self.OnRun).start()
		
		self.ShowModal()
		self.Destroy()
		return

	def OnRun(self):
		wx.CallAfter(self.updateLabel, "读取固件...")
		hexFile = intelHex.readHex(self.filename)
		wx.CallAfter(self.updateLabel, "连接打印机...")
		programmer = stk500v2.Stk500v2()
		programmer.progressCallback = self.OnProgress
		if self.port == 'AUTO':
			for self.port in machineCom.serialList(True):
				try:
					programmer.connect(self.port)
					break
				except ispBase.IspError:
					pass
		else:
			try:
				programmer.connect(self.port)
			except ispBase.IspError:
				pass
				
		if programmer.isConnected():
			wx.CallAfter(self.updateLabel, "上传固件...")
			try:
				programmer.programChip(hexFile)
				wx.CallAfter(self.updateLabel, "完成!\n已安装固件: %s" % (os.path.basename(self.filename)))
			except ispBase.IspError as e:
				wx.CallAfter(self.updateLabel, "固件写入失败\n" + str(e))
				
			programmer.close()
			wx.CallAfter(self.okButton.Enable)
			return
		wx.MessageBox('找不到打印机\n您的打印机是否正确连接到电脑？', '固件升级', wx.OK | wx.ICON_ERROR)
		wx.CallAfter(self.Close)
	
	def updateLabel(self, text):
		self.progressLabel.SetLabel(text)
		#self.Layout()

	def OnProgress(self, value, max):
		wx.CallAfter(self.progressGauge.SetRange, max)
		wx.CallAfter(self.progressGauge.SetValue, value)

	def OnOk(self, e):
		self.Close()

	def OnClose(self, e):
		self.Destroy()

