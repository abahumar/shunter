"""
Sector rotation analysis — identify which sectors are trending up/down.
"""

import pandas as pd
from typing import Dict, List, Tuple

from scanner.symbols import SYMBOLS
from scanner.indicators import compute_indicators, get_latest_indicators
from scanner.signals import analyze_stock


SECTOR_MAP = {
    # Industrial
    "7086.KL": "Industrial", "5198.KL": "Industrial", "7219.KL": "Industrial",
    "7609.KL": "Industrial", "4758.KL": "Industrial", "6556.KL": "Industrial",
    "5015.KL": "Industrial", "7214.KL": "Industrial", "7020.KL": "Industrial",
    "7162.KL": "Industrial", "5302.KL": "Industrial", "7579.KL": "Industrial",
    "5021.KL": "Industrial", "7005.KL": "Industrial", "6998.KL": "Industrial",
    "7036.KL": "Industrial", "5100.KL": "Industrial", "7221.KL": "Industrial",
    "2852.KL": "Industrial", "7076.KL": "Industrial", "8052.KL": "Industrial",
    "5273.KL": "Industrial", "5007.KL": "Industrial", "5797.KL": "Industrial",
    "7016.KL": "Industrial", "7245.KL": "Industrial", "7018.KL": "Industrial",
    "2127.KL": "Industrial", "5037.KL": "Industrial", "8435.KL": "Industrial",
    "5317.KL": "Industrial", "0291.KL": "Industrial", "5094.KL": "Industrial",
    "7157.KL": "Industrial", "5276.KL": "Industrial", "7212.KL": "Industrial",
    "5165.KL": "Industrial", "7114.KL": "Industrial", "7169.KL": "Industrial",
    "0269.KL": "Industrial", "7233.KL": "Industrial", "0064.KL": "Industrial",
    "8907.KL": "Industrial", "5208.KL": "Industrial", "5056.KL": "Industrial",
    "7217.KL": "Industrial", "7773.KL": "Industrial", "5101.KL": "Industrial",
    "7229.KL": "Industrial", "5322.KL": "Industrial", "3107.KL": "Industrial",
    "9318.KL": "Industrial", "5197.KL": "Industrial", "5277.KL": "Industrial",
    "7197.KL": "Industrial", "0039.KL": "Industrial", "7192.KL": "Industrial",
    "5220.KL": "Industrial", "5649.KL": "Industrial", "3247.KL": "Industrial",
    "0296.KL": "Industrial", "5095.KL": "Industrial", "5151.KL": "Industrial",
    "0161.KL": "Industrial", "5072.KL": "Industrial", "8443.KL": "Industrial",
    "9601.KL": "Industrial", "5291.KL": "Industrial", "0185.KL": "Industrial",
    "5000.KL": "Industrial", "5178.KL": "Industrial", "6874.KL": "Industrial",
    "5673.KL": "Industrial", "5192.KL": "Industrial", "0054.KL": "Industrial",
    "7199.KL": "Industrial", "0151.KL": "Industrial", "6211.KL": "Industrial",
    "5371.KL": "Industrial", "9466.KL": "Industrial", "5035.KL": "Industrial",
    "6971.KL": "Industrial", "7017.KL": "Industrial", "9121.KL": "Industrial",
    "6491.KL": "Industrial", "7033.KL": "Industrial", "9083.KL": "Industrial",
    "5843.KL": "Industrial", "8362.KL": "Industrial", "0268.KL": "Industrial",
    "9326.KL": "Industrial", "9881.KL": "Industrial", "7170.KL": "Industrial",
    "4235.KL": "Industrial", "8486.KL": "Industrial", "5068.KL": "Industrial",
    "5143.KL": "Industrial", "3794.KL": "Industrial", "5916.KL": "Industrial",
    "5098.KL": "Industrial", "7029.KL": "Industrial", "7123.KL": "Industrial",
    "7099.KL": "Industrial", "7004.KL": "Industrial", "3778.KL": "Industrial",
    "0207.KL": "Industrial", "0043.KL": "Industrial", "5001.KL": "Industrial",
    "5576.KL": "Industrial", "5152.KL": "Industrial", "3883.KL": "Industrial",
    "5087.KL": "Industrial", "0270.KL": "Industrial", "7241.KL": "Industrial",
    "7140.KL": "Industrial", "5298.KL": "Industrial", "5065.KL": "Industrial",
    "7225.KL": "Industrial", "7095.KL": "Industrial", "8419.KL": "Industrial",
    "5331.KL": "Industrial", "5125.KL": "Industrial", "5271.KL": "Industrial",
    "5436.KL": "Industrial", "5219.KL": "Industrial", "5183.KL": "Industrial",
    "8117.KL": "Industrial", "7163.KL": "Industrial", "7172.KL": "Industrial",
    "6637.KL": "Industrial", "8869.KL": "Industrial", "9873.KL": "Industrial",
    "7201.KL": "Industrial", "0196.KL": "Industrial", "7498.KL": "Industrial",
    "7232.KL": "Industrial", "9954.KL": "Industrial", "9741.KL": "Industrial",
    "8745.KL": "Industrial", "9822.KL": "Industrial", "5147.KL": "Industrial",
    "7811.KL": "Industrial", "9237.KL": "Industrial", "7239.KL": "Industrial",
    "4731.KL": "Industrial", "8125.KL": "Industrial", "7073.KL": "Industrial",
    "5308.KL": "Industrial", "5163.KL": "Industrial", "7115.KL": "Industrial",
    "7155.KL": "Industrial", "7248.KL": "Industrial", "7132.KL": "Industrial",
    "5134.KL": "Industrial", "0225.KL": "Industrial", "7207.KL": "Industrial",
    "5211.KL": "Industrial", "7235.KL": "Industrial", "7097.KL": "Industrial",
    "5289.KL": "Industrial", "8702.KL": "Industrial", "7034.KL": "Industrial",
    "7854.KL": "Industrial", "5330.KL": "Industrial", "7285.KL": "Industrial",
    "5010.KL": "Industrial", "7173.KL": "Industrial", "7100.KL": "Industrial",
    "1368.KL": "Industrial", "7137.KL": "Industrial", "5340.KL": "Industrial",
    "7091.KL": "Industrial", "0257.KL": "Industrial", "7133.KL": "Industrial",
    "6963.KL": "Industrial", "4243.KL": "Industrial", "8176.KL": "Industrial",
    "7231.KL": "Industrial", "5009.KL": "Industrial", "7050.KL": "Industrial",
    "7025.KL": "Industrial", "5048.KL": "Industrial", "7014.KL": "Industrial",

    # Consumer
    "7167.KL": "Consumer", "1481.KL": "Consumer", "6599.KL": "Consumer",
    "7315.KL": "Consumer", "5238.KL": "Consumer", "2658.KL": "Consumer",
    "6351.KL": "Consumer", "6432.KL": "Consumer", "7722.KL": "Consumer",
    "8885.KL": "Consumer", "5196.KL": "Consumer", "5248.KL": "Consumer",
    "9288.KL": "Consumer", "2828.KL": "Consumer", "7174.KL": "Consumer",
    "7128.KL": "Consumer", "5099.KL": "Consumer", "7035.KL": "Consumer",
    "7209.KL": "Consumer", "5104.KL": "Consumer", "5336.KL": "Consumer",
    "9423.KL": "Consumer", "5166.KL": "Consumer", "1619.KL": "Consumer",
    "3026.KL": "Consumer", "5318.KL": "Consumer", "0239.KL": "Consumer",
    "5337.KL": "Consumer", "9091.KL": "Consumer", "7149.KL": "Consumer",
    "5081.KL": "Consumer", "7208.KL": "Consumer", "1287.KL": "Consumer",
    "5306.KL": "Consumer", "8605.KL": "Consumer", "6939.KL": "Consumer",
    "0157.KL": "Consumer", "9172.KL": "Consumer", "3689.KL": "Consumer",
    "7184.KL": "Consumer", "5592.KL": "Consumer", "7943.KL": "Consumer",
    "0136.KL": "Consumer", "5102.KL": "Consumer", "5335.KL": "Consumer",
    "5160.KL": "Consumer", "3301.KL": "Consumer", "5024.KL": "Consumer",
    "8478.KL": "Consumer", "9113.KL": "Consumer", "7223.KL": "Consumer",
    "7152.KL": "Consumer", "8672.KL": "Consumer", "5247.KL": "Consumer",
    "7216.KL": "Consumer", "7062.KL": "Consumer", "0180.KL": "Consumer",
    "9385.KL": "Consumer", "8079.KL": "Consumer", "5328.KL": "Consumer",
    "7089.KL": "Consumer", "7234.KL": "Consumer", "8303.KL": "Consumer",
    "7085.KL": "Consumer", "7243.KL": "Consumer", "7087.KL": "Consumer",
    "5983.KL": "Consumer", "2097.KL": "Consumer", "7935.KL": "Consumer",
    "0229.KL": "Consumer", "5296.KL": "Consumer", "5202.KL": "Consumer",
    "5316.KL": "Consumer", "4707.KL": "Consumer", "7060.KL": "Consumer",
    "7154.KL": "Consumer", "7215.KL": "Consumer", "7139.KL": "Consumer",
    "5066.KL": "Consumer", "5533.KL": "Consumer", "0049.KL": "Consumer",
    "5079.KL": "Consumer", "5260.KL": "Consumer", "7107.KL": "Consumer",
    "7052.KL": "Consumer", "4081.KL": "Consumer", "5022.KL": "Consumer",
    "9407.KL": "Consumer", "5657.KL": "Consumer", "9997.KL": "Consumer",
    "0186.KL": "Consumer", "7080.KL": "Consumer", "8532.KL": "Consumer",
    "5681.KL": "Consumer", "5080.KL": "Consumer", "7237.KL": "Consumer",
    "4065.KL": "Consumer", "7168.KL": "Consumer", "7134.KL": "Consumer",
    "7084.KL": "Consumer", "9946.KL": "Consumer", "0183.KL": "Consumer",
    "5157.KL": "Consumer", "0212.KL": "Consumer", "9792.KL": "Consumer",
    "5305.KL": "Consumer", "7180.KL": "Consumer", "7412.KL": "Consumer",
    "7246.KL": "Consumer", "4197.KL": "Consumer", "5172.KL": "Consumer",
    "9776.KL": "Consumer", "5242.KL": "Consumer", "7103.KL": "Consumer",
    "7186.KL": "Consumer", "7211.KL": "Consumer", "4405.KL": "Consumer",
    "8966.KL": "Consumer", "7439.KL": "Consumer", "7200.KL": "Consumer",
    "9369.KL": "Consumer", "7252.KL": "Consumer", "0012.KL": "Consumer",
    "7230.KL": "Consumer", "7176.KL": "Consumer", "7757.KL": "Consumer",
    "4995.KL": "Consumer", "7203.KL": "Consumer", "5016.KL": "Consumer",
    "0197.KL": "Consumer", "7121.KL": "Consumer", "5159.KL": "Consumer",
    "0250.KL": "Consumer", "5131.KL": "Consumer",

    # Technology
    "7181.KL": "Technology", "5204.KL": "Technology", "5195.KL": "Technology",
    "0277.KL": "Technology", "0246.KL": "Technology", "5301.KL": "Technology",
    "0051.KL": "Technology", "7204.KL": "Technology", "4456.KL": "Technology",
    "8338.KL": "Technology", "5036.KL": "Technology", "0065.KL": "Technology",
    "0128.KL": "Technology", "9377.KL": "Technology", "0104.KL": "Technology",
    "7022.KL": "Technology", "0208.KL": "Technology", "0082.KL": "Technology",
    "5028.KL": "Technology", "0166.KL": "Technology", "9393.KL": "Technology",
    "0253.KL": "Technology", "5309.KL": "Technology", "5161.KL": "Technology",
    "0146.KL": "Technology", "0127.KL": "Technology", "9334.KL": "Technology",
    "0143.KL": "Technology", "3867.KL": "Technology", "5011.KL": "Technology",
    "5286.KL": "Technology", "0126.KL": "Technology", "0113.KL": "Technology",
    "5216.KL": "Technology", "0083.KL": "Technology", "9008.KL": "Technology",
    "0040.KL": "Technology", "7160.KL": "Technology", "0200.KL": "Technology",
    "0259.KL": "Technology", "9075.KL": "Technology", "4359.KL": "Technology",
    "5005.KL": "Technology", "5292.KL": "Technology", "0097.KL": "Technology",
    "5162.KL": "Technology", "0008.KL": "Technology", "0138.KL": "Technology",

    # Property
    "7131.KL": "Property", "7007.KL": "Property", "4057.KL": "Property",
    "5182.KL": "Property", "7120.KL": "Property", "6602.KL": "Property",
    "6378.KL": "Property", "9814.KL": "Property", "6173.KL": "Property",
    "7187.KL": "Property", "5738.KL": "Property", "5049.KL": "Property",
    "6718.KL": "Property", "7198.KL": "Property", "8206.KL": "Property",
    "3557.KL": "Property", "6076.KL": "Property", "6815.KL": "Property",
    "6041.KL": "Property", "1147.KL": "Property", "5020.KL": "Property",
    "9962.KL": "Property", "7105.KL": "Property", "5062.KL": "Property",
    "4251.KL": "Property", "5084.KL": "Property", "9687.KL": "Property",
    "5249.KL": "Property", "1589.KL": "Property", "8923.KL": "Property",
    "6769.KL": "Property", "7077.KL": "Property", "5038.KL": "Property",
    "7179.KL": "Property", "3174.KL": "Property", "8494.KL": "Property",
    "5789.KL": "Property", "3573.KL": "Property", "7617.KL": "Property",
    "8583.KL": "Property", "8141.KL": "Property", "1651.KL": "Property",
    "6181.KL": "Property", "5236.KL": "Property", "4022.KL": "Property",
    "1694.KL": "Property", "5040.KL": "Property", "8893.KL": "Property",
    "6114.KL": "Property", "3913.KL": "Property", "5073.KL": "Property",
    "0056.KL": "Property", "5827.KL": "Property", "3611.KL": "Property",
    "1724.KL": "Property", "2682.KL": "Property", "6912.KL": "Property",
    "7055.KL": "Property", "5075.KL": "Property", "7010.KL": "Property",
    "5313.KL": "Property", "7765.KL": "Property", "8664.KL": "Property",
    "4596.KL": "Property", "5207.KL": "Property", "4286.KL": "Property",
    "2224.KL": "Property", "5288.KL": "Property", "7249.KL": "Property",
    "5315.KL": "Property", "4375.KL": "Property", "3743.KL": "Property",
    "1538.KL": "Property", "2259.KL": "Property", "5191.KL": "Property",
    "2429.KL": "Property", "0230.KL": "Property", "5239.KL": "Property",
    "5401.KL": "Property", "7079.KL": "Property", "5148.KL": "Property",
    "5200.KL": "Property", "7003.KL": "Property", "3158.KL": "Property",
    "7066.KL": "Property",

    # Construction
    "7078.KL": "Construction", "5293.KL": "Construction", "5190.KL": "Construction",
    "5932.KL": "Construction", "7195.KL": "Construction", "8591.KL": "Construction",
    "7528.KL": "Construction", "5253.KL": "Construction", "8877.KL": "Construction",
    "4847.KL": "Construction", "5205.KL": "Construction", "7047.KL": "Construction",
    "5226.KL": "Construction", "9261.KL": "Construction", "5398.KL": "Construction",
    "0198.KL": "Construction", "5169.KL": "Construction", "3336.KL": "Construction",
    "7240.KL": "Construction", "0192.KL": "Construction", "8834.KL": "Construction",
    "4723.KL": "Construction", "7161.KL": "Construction", "5171.KL": "Construction",
    "5310.KL": "Construction", "9628.KL": "Construction", "5129.KL": "Construction",
    "8192.KL": "Construction", "7595.KL": "Construction", "9571.KL": "Construction",
    "5085.KL": "Construction", "5703.KL": "Construction", "7071.KL": "Construction",
    "8311.KL": "Construction", "5622.KL": "Construction", "9598.KL": "Construction",
    "5070.KL": "Construction", "6807.KL": "Construction", "5263.KL": "Construction",
    "9717.KL": "Construction", "5054.KL": "Construction", "5042.KL": "Construction",
    "5297.KL": "Construction", "7145.KL": "Construction", "5006.KL": "Construction",
    "7070.KL": "Construction", "9679.KL": "Construction", "7028.KL": "Construction",
    "2283.KL": "Construction",

    # Energy
    "5115.KL": "Energy", "0168.KL": "Energy", "5210.KL": "Energy",
    "5257.KL": "Energy", "5184.KL": "Energy", "5141.KL": "Energy",
    "5132.KL": "Energy", "7277.KL": "Energy", "8613.KL": "Energy",
    "7253.KL": "Energy", "5199.KL": "Energy", "5321.KL": "Energy",
    "0193.KL": "Energy", "5255.KL": "Energy", "5186.KL": "Energy",
    "7108.KL": "Energy", "5133.KL": "Energy", "3042.KL": "Energy",
    "0091.KL": "Energy", "7130.KL": "Energy", "0219.KL": "Energy",
    "0223.KL": "Energy", "0215.KL": "Energy", "7228.KL": "Energy",
    "2739.KL": "Energy", "0118.KL": "Energy", "7250.KL": "Energy",
    "5218.KL": "Energy", "5243.KL": "Energy", "5142.KL": "Energy",

    # Plantation
    "7054.KL": "Plantation", "1899.KL": "Plantation", "5069.KL": "Plantation",
    "8982.KL": "Plantation", "5029.KL": "Plantation", "2291.KL": "Plantation",
    "7382.KL": "Plantation", "2135.KL": "Plantation", "5138.KL": "Plantation",
    "7501.KL": "Plantation", "2607.KL": "Plantation", "6262.KL": "Plantation",
    "1961.KL": "Plantation", "4383.KL": "Plantation", "5323.KL": "Plantation",
    "5027.KL": "Plantation", "1996.KL": "Plantation", "2445.KL": "Plantation",
    "5223.KL": "Plantation", "5026.KL": "Plantation", "5319.KL": "Plantation",
    "9695.KL": "Plantation", "5113.KL": "Plantation", "2542.KL": "Plantation",
    "5126.KL": "Plantation", "5135.KL": "Plantation", "5285.KL": "Plantation",
    "4316.KL": "Plantation", "5012.KL": "Plantation", "2054.KL": "Plantation",
    "5112.KL": "Plantation", "9059.KL": "Plantation", "2593.KL": "Plantation",
    "2089.KL": "Plantation",

    # Transport
    "7218.KL": "Transport", "5259.KL": "Transport", "5032.KL": "Transport",
    "7117.KL": "Transport", "7210.KL": "Transport", "7676.KL": "Transport",
    "0078.KL": "Transport", "2062.KL": "Transport", "5136.KL": "Transport",
    "7013.KL": "Transport", "5078.KL": "Transport", "3816.KL": "Transport",
    "8346.KL": "Transport", "4634.KL": "Transport", "5145.KL": "Transport",
    "7053.KL": "Transport", "5173.KL": "Transport", "6521.KL": "Transport",
    "5303.KL": "Transport", "5149.KL": "Transport", "5140.KL": "Transport",
    "5246.KL": "Transport", "5267.KL": "Transport",

    # Healthcare
    "7191.KL": "Healthcare", "7090.KL": "Healthcare", "0163.KL": "Healthcare",
    "7148.KL": "Healthcare", "5168.KL": "Healthcare", "7803.KL": "Healthcare",
    "5225.KL": "Healthcare", "7153.KL": "Healthcare", "0002.KL": "Healthcare",
    "5878.KL": "Healthcare", "0201.KL": "Healthcare", "0222.KL": "Healthcare",
    "7081.KL": "Healthcare", "0001.KL": "Healthcare", "0101.KL": "Healthcare",
    "7113.KL": "Healthcare", "0256.KL": "Healthcare", "7178.KL": "Healthcare",

    # Telecom
    "7031.KL": "Telecom", "6888.KL": "Telecom", "6947.KL": "Telecom",
    "0059.KL": "Telecom", "6012.KL": "Telecom", "5090.KL": "Telecom",
    "0159.KL": "Telecom", "0172.KL": "Telecom", "5332.KL": "Telecom",
    "0032.KL": "Telecom", "5252.KL": "Telecom", "9431.KL": "Telecom",
    "4863.KL": "Telecom", "5031.KL": "Telecom",

    # Utilities
    "7471.KL": "Utilities", "5209.KL": "Utilities", "5264.KL": "Utilities",
    "3069.KL": "Utilities", "5041.KL": "Utilities", "6033.KL": "Utilities",
    "5272.KL": "Utilities", "8567.KL": "Utilities", "8524.KL": "Utilities",
    "5347.KL": "Utilities",

    # Finance
    "5258.KL": "Finance", "1818.KL": "Finance", "1171.KL": "Finance",
    "9296.KL": "Finance", "6139.KL": "Finance",

    # Industrial
    "0218.KL": "Industrial", "0038.KL": "Industrial", "0105.KL": "Industrial",
    "0362.KL": "Industrial", "0098.KL": "Industrial", "0187.KL": "Industrial",
    "0263.KL": "Industrial", "0313.KL": "Industrial", "0339.KL": "Industrial",
    "0238.KL": "Industrial", "0348.KL": "Industrial", "0341.KL": "Industrial",
    "0240.KL": "Industrial", "0323.KL": "Industrial", "0331.KL": "Industrial",
    "0227.KL": "Industrial", "0317.KL": "Industrial", "0072.KL": "Industrial",
    "0100.KL": "Industrial", "0190.KL": "Industrial", "0370.KL": "Industrial",
    "0084.KL": "Industrial", "0355.KL": "Industrial", "0231.KL": "Industrial",
    "0284.KL": "Industrial", "0175.KL": "Industrial", "0160.KL": "Industrial",
    "0188.KL": "Industrial", "0228.KL": "Industrial", "0366.KL": "Industrial",
    "0376.KL": "Industrial", "0024.KL": "Industrial", "0307.KL": "Industrial",
    "0293.KL": "Industrial", "0266.KL": "Industrial", "0295.KL": "Industrial",
    "0167.KL": "Industrial", "0288.KL": "Industrial", "0350.KL": "Industrial",
    "0213.KL": "Industrial", "0325.KL": "Industrial", "0368.KL": "Industrial",
    "0361.KL": "Industrial", "0177.KL": "Industrial", "0289.KL": "Industrial",
    "0379.KL": "Industrial", "0381.KL": "Industrial", "0377.KL": "Industrial",
    "0217.KL": "Industrial", "0081.KL": "Industrial", "0133.KL": "Industrial",
    "0028.KL": "Industrial", "0055.KL": "Industrial", "0306.KL": "Industrial",
    "0321.KL": "Industrial", "0349.KL": "Industrial", "0337.KL": "Industrial",
    "0211.KL": "Industrial", "0089.KL": "Industrial", "0302.KL": "Industrial",
    "0297.KL": "Industrial", "0232.KL": "Industrial", "0102.KL": "Industrial",
    "0298.KL": "Industrial", "0353.KL": "Industrial", "0352.KL": "Industrial",
    "0025.KL": "Industrial", "0248.KL": "Industrial", "0301.KL": "Industrial",

    # Consumer
    "0365.KL": "Consumer", "0309.KL": "Consumer", "0380.KL": "Consumer",
    "0179.KL": "Consumer", "0335.KL": "Consumer", "0281.KL": "Consumer",
    "0205.KL": "Consumer", "0304.KL": "Consumer", "0378.KL": "Consumer",
    "0170.KL": "Consumer", "0357.KL": "Consumer", "0327.KL": "Consumer",
    "0312.KL": "Consumer", "0252.KL": "Consumer", "0338.KL": "Consumer",
    "0022.KL": "Consumer", "0356.KL": "Consumer", "0260.KL": "Consumer",
    "0342.KL": "Consumer", "0300.KL": "Consumer", "0158.KL": "Consumer",
    "0178.KL": "Consumer", "0316.KL": "Consumer", "0326.KL": "Consumer",
    "0216.KL": "Consumer", "0287.KL": "Consumer", "0330.KL": "Consumer",
    "0279.KL": "Consumer", "0333.KL": "Consumer", "0271.KL": "Consumer",

    # Technology
    "0181.KL": "Technology", "0258.KL": "Technology", "0209.KL": "Technology",
    "0079.KL": "Technology", "0068.KL": "Technology", "0191.KL": "Technology",
    "0131.KL": "Technology", "0267.KL": "Technology", "0278.KL": "Technology",
    "0107.KL": "Technology", "0174.KL": "Technology", "0311.KL": "Technology",
    "0060.KL": "Technology", "0358.KL": "Technology", "0023.KL": "Technology",
    "0265.KL": "Technology", "0010.KL": "Technology", "0036.KL": "Technology",
    "0111.KL": "Technology", "0176.KL": "Technology", "0249.KL": "Technology",
    "0156.KL": "Technology", "0112.KL": "Technology", "0070.KL": "Technology",
    "0026.KL": "Technology", "0275.KL": "Technology", "0290.KL": "Technology",
    "0202.KL": "Technology", "0236.KL": "Technology", "0203.KL": "Technology",
    "0251.KL": "Technology", "0117.KL": "Technology", "0093.KL": "Technology",
    "0050.KL": "Technology", "0132.KL": "Technology", "0343.KL": "Technology",
    "0145.KL": "Technology", "0375.KL": "Technology", "0272.KL": "Technology",
    "0319.KL": "Technology", "0069.KL": "Technology", "0086.KL": "Technology",
    "0094.KL": "Technology",

    # Property
    "0308.KL": "Property",

    # Construction
    "0226.KL": "Construction", "0372.KL": "Construction", "0345.KL": "Construction",
    "0206.KL": "Construction", "0237.KL": "Construction", "0359.KL": "Construction",
    "0292.KL": "Construction", "0351.KL": "Construction", "0245.KL": "Construction",
    "0235.KL": "Construction", "0109.KL": "Construction", "0360.KL": "Construction",
    "0045.KL": "Construction", "0241.KL": "Construction", "0221.KL": "Construction",
    "0310.KL": "Construction", "0273.KL": "Construction", "0347.KL": "Construction",
    "0162.KL": "Construction",

    # Energy
    "0318.KL": "Energy", "0367.KL": "Energy", "0369.KL": "Energy",
    "0233.KL": "Energy", "0320.KL": "Energy", "0262.KL": "Energy",
    "0373.KL": "Energy",

    # Transport
    "0299.KL": "Transport", "0048.KL": "Transport", "0282.KL": "Transport",
    "0034.KL": "Transport", "0305.KL": "Transport", "0080.KL": "Transport",
    "0199.KL": "Transport",

    # Healthcare
    "0243.KL": "Healthcare", "0283.KL": "Healthcare", "0155.KL": "Healthcare",
    "0329.KL": "Healthcare", "0363.KL": "Healthcare", "0332.KL": "Healthcare",

    # Telecom
    "0195.KL": "Telecom", "0035.KL": "Telecom", "0096.KL": "Telecom",
    "0123.KL": "Telecom", "0007.KL": "Telecom", "0129.KL": "Telecom",
    "0165.KL": "Telecom", "0017.KL": "Telecom",

    # Utilities
    "0011.KL": "Utilities",

    # Industrial
    "03024.KL": "Industrial", "03029.KL": "Industrial", "03060.KL": "Industrial",
    "03040.KL": "Industrial", "03027.KL": "Industrial", "03031.KL": "Industrial",
    "03052.KL": "Industrial", "03033.KL": "Industrial", "03061.KL": "Industrial",
    "03062.KL": "Industrial", "03043.KL": "Industrial",

    # Consumer
    "03051.KL": "Consumer", "03037.KL": "Consumer", "03012.KL": "Consumer",
    "03053.KL": "Consumer", "03025.KL": "Consumer", "03015.KL": "Consumer",
    "03019.KL": "Consumer", "03064.KL": "Consumer", "03063.KL": "Consumer",
    "03009.KL": "Consumer",

    # Technology
    "03011.KL": "Technology", "03001.KL": "Technology", "03036.KL": "Technology",
    "03039.KL": "Technology", "03057.KL": "Technology", "03008.KL": "Technology",

    # Construction
    "03042.KL": "Construction", "03065.KL": "Construction", "03050.KL": "Construction",
    "03017.KL": "Construction",

    # Plantation
    "03055.KL": "Plantation",

    # Healthcare
    "03023.KL": "Healthcare",

    # Finance
    "03059.KL": "Finance", "5320.KL": "Finance",
}


def get_sector(symbol: str) -> str:
    """Get sector for a stock symbol."""
    return SECTOR_MAP.get(symbol, "Others")


def analyze_sectors(stock_data: Dict[str, pd.DataFrame]) -> List[dict]:
    """
    Analyze sector performance and momentum.
    Returns list of sector dicts sorted by strength.
    """
    sector_stocks = {}  # sector -> list of (symbol, indicators)

    for symbol, df in stock_data.items():
        sector = get_sector(symbol)
        try:
            df = compute_indicators(df)
            ind = get_latest_indicators(df)
            if ind.get("close") is None:
                continue

            analysis = analyze_stock(ind)

            # Calculate price change %
            if len(df) >= 20:
                pct_1m = ((ind["close"] - df.iloc[-20]["Close"]) / df.iloc[-20]["Close"]) * 100
            else:
                pct_1m = 0

            if sector not in sector_stocks:
                sector_stocks[sector] = []
            sector_stocks[sector].append({
                "symbol": symbol,
                "close": ind["close"],
                "rsi": ind.get("rsi", 50),
                "adx": ind.get("adx", 0),
                "signal": analysis["signal"],
                "net_score": analysis["net_score"],
                "pct_1m": pct_1m,
            })
        except Exception:
            continue

    # Aggregate per sector
    results = []
    for sector, stocks in sector_stocks.items():
        if not stocks:
            continue

        avg_score = sum(s["net_score"] for s in stocks) / len(stocks)
        avg_rsi = sum(s["rsi"] for s in stocks) / len(stocks)
        avg_pct = sum(s["pct_1m"] for s in stocks) / len(stocks)
        buy_count = sum(1 for s in stocks if s["signal"] in ("BUY", "STRONG BUY"))
        sell_count = sum(1 for s in stocks if s["signal"] in ("SELL", "STRONG SELL"))

        if avg_score >= 30:
            trend = "🟢 HOT"
        elif avg_score >= 10:
            trend = "🟡 WARM"
        elif avg_score >= -10:
            trend = "⚪ NEUTRAL"
        else:
            trend = "🔴 COLD"

        results.append({
            "sector": sector,
            "trend": trend,
            "avg_score": avg_score,
            "avg_rsi": avg_rsi,
            "avg_pct_1m": avg_pct,
            "stock_count": len(stocks),
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "top_stock": max(stocks, key=lambda s: s["net_score"]),
        })

    results.sort(key=lambda x: x["avg_score"], reverse=True)
    return results
