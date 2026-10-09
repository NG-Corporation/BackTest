from datetime import timedelta
from enum import Enum
import numpy as np

class TimeFrame(Enum):
    H4 = 1
    M15 = 2

# swing structure direct Bullish to Bearish
def implement_market_structure_states_direct(df, n=5):
    """Calcule les états du marché avec transition obligatoire par l'état NEUTRAL.

    Aucun passage direct entre BULLISH et BEARISH n'est autorisé.
    """
    df = df.copy()
    length = len(df)

    df['is_swing_high'] = False
    df['is_swing_low'] = False
    for k in range(n, len(df) - n):
        # Le plus haut des n bougies précédentes et suivantes
        high_range = df['High'].iloc[k - n:k + n + 1]
        if df['High'].iloc[k] == high_range.max():
            df.loc[df.index[k], 'is_swing_high'] = True
            
        # Le plus bas des n bougies précédentes et suivantes
        low_range = df['Low'].iloc[k - n:k + n + 1]
        if df['Low'].iloc[k] == low_range.min():
            df.loc[df.index[k], 'is_swing_low'] = True

    states = []
    current_state = None

    # Variables de structure de marché
    higher_low = None  # Le plancher (uniquement actif en BULLISH)
    lower_high = None  # Le plafond (uniquement actif en BEARISH)

    for j in range(length):
        close_p = df["Close"].iloc[j]

        # --- ÉTAPE B : Machine à états avec transit strict par NEUTRAL ---
        if current_state == "BULLISH" or current_state is None:
            # Sortie de Bullish : Clôture sous le Higher Low (HL) -> NEUTRAL uniquement
            if higher_low is not None and close_p < higher_low:
                current_state = "BEARISH"

        elif current_state == "BEARISH" or current_state is None:
            # Sortie de Bearish : Clôture au-dessus du Lower High (LH) -> NEUTRAL uniquement
            if lower_high is not None and close_p > lower_high:
                current_state = "BULLISH"

        states.append(current_state)

         # --- ÉTAPE A : Enregistrement des Swings dès qu'ils se confirment ---
        if df["is_swing_high"].iloc[j] == True:
            lower_high = df["High"].iloc[j]

        if df["is_swing_low"].iloc[j] == True:
            higher_low = df["Low"].iloc[j]


    df["market_state"] = states
    return df

# swing structure direct Bullish to Bearish
def implement_market_structure_states_fixed_pivots(df, n=5):
    """Calcule les états du marché avec transition obligatoire par l'état NEUTRAL.

    Aucun passage direct entre BULLISH et BEARISH n'est autorisé.
    """
    df = df.copy()
    length = len(df)

    df['is_swing_high'] = False
    df['is_swing_low'] = False
    for k in range(n, len(df) - n):
        # Le plus haut des n bougies précédentes et suivantes
        high_range = df['High'].iloc[k - n:k + n + 1]
        if df['High'].iloc[k] == high_range.max():
            df.loc[df.index[k], 'is_swing_high'] = True
            
        # Le plus bas des n bougies précédentes et suivantes
        low_range = df['Low'].iloc[k - n:k + n + 1]
        if df['Low'].iloc[k] == low_range.min():
            df.loc[df.index[k], 'is_swing_low'] = True

    states = []
    current_state = None

    # Variables de structure de marché
    last_confirmed_high = None
    last_confirmed_low = None
    higher_low = None  # Le plancher (uniquement actif en BULLISH)
    lower_high = None  # Le plafond (uniquement actif en BEARISH)

    for j in range(length):
        close_p = df["Close"].iloc[j]

        # --- ÉTAPE A : Enregistrement des Swings dès qu'ils se confirment ---
        if df["is_swing_high"].iloc[j] == True:
            lower_high = df["High"].iloc[j]
            if last_confirmed_high is None:
                last_confirmed_high = lower_high

            if last_confirmed_high > lower_high:
                last_confirmed_high = lower_high

        if df["is_swing_low"].iloc[j] == True:
            higher_low = df["Low"].iloc[j]
            if last_confirmed_low is None:
                last_confirmed_low = higher_low

            if last_confirmed_low < higher_low:
                last_confirmed_low = higher_low

        # --- ÉTAPE B : Machine à états avec transit strict par NEUTRAL ---
        if current_state == "BULLISH" or current_state is None:
            # Sortie de Bullish : Clôture sous le Higher Low (HL) -> NEUTRAL uniquement
            if last_confirmed_low is not None and lower_high is not None and close_p < last_confirmed_low:
                current_state = "BEARISH"
                last_confirmed_high = lower_high

        elif current_state == "BEARISH" or current_state is None:
            # Sortie de Bearish : Clôture au-dessus du Lower High (LH) -> NEUTRAL uniquement
            if last_confirmed_high is not None and higher_low is not None and close_p > last_confirmed_high:
                current_state = "BULLISH"
                last_confirmed_low = higher_low

        states.append(current_state)

    df["market_state"] = states
    return df


# define resistant level
def define_resistant_level(df, define_key_level_window = 20):
    # gap
    gap = 0.3

    # all resistant highs
    resistant_list = []
    
    for row in df.iterrows():
        start_index = row[0] - timedelta(days=define_key_level_window)
        back_candle_range = df.loc[start_index:row[0]]
        pivot_lows = back_candle_range[back_candle_range['is_swing_low'] == True]

        for candle in pivot_lows.iterrows():
            frequency = 0
            total_candle = 0
            # resistant highs related to current high
            resistant_zone = []

            for candle2 in pivot_lows.iterrows():
                # candle 2 date needs to be before candle date
                if (candle2[0] <= candle[0] and 
                    candle[1]['Low'] + gap > candle2[1]['Low'] and 
                    candle[1]['Low'] - gap < candle2[1]['Low']):
                    frequency += 1
                    total_candle += candle2[1]['Low']
                    # resistant_zone.append(candle2)

            if frequency > 2:
                mean_candle = round(total_candle / frequency, 3)
                resistant_zone.append(candle)

                # for all new resistant, check if the candle is in resistant list, if not add it
                for i in range(len(resistant_zone)):
                    is_resistant = False

                    for j in range(len(resistant_list)):
                        if resistant_zone[i][0] == resistant_list[j][0][0]:
                            # print(f"{resistant_zone[i][0]} = {resistant_list[j][0][0]}")
                            is_resistant = True

                    if not is_resistant:
                        # print(f"{resistant_zone[i][0]} mean_candle = {mean_candle} & frequency = {frequency}")
                        resistant_candle = [resistant_zone[i], mean_candle]
                        resistant_list.append(resistant_candle)

    # print(resistant_list)
    return resistant_list

# define resistant level
def define_resistant_level_with_atr(df, define_key_level_window = 120, atr_multiplier=0.8, min_touched=3):
    # all resistant highs
    resistant_list = []
    
    for index in range(len(df)):
        back_candle_range = df.iloc[index-define_key_level_window:index]
        pivot_lows = back_candle_range[back_candle_range['is_swing_low'] == True]

        for candle in pivot_lows.iterrows():
            frequency = 0
            total_candle = 0
            # resistant highs related to current high
            resistant_zone = []

            for candle2 in pivot_lows.iterrows():
                # candle 2 date needs to be before candle date
                if (candle2[0] <= candle[0] and 
                    candle[1]['Low'] + candle[1]['ATR']*atr_multiplier > candle2[1]['Low'] and 
                    candle[1]['Low'] - candle[1]['ATR']*atr_multiplier < candle2[1]['Low']):
                    frequency += 1
                    total_candle += candle2[1]['Low']
                    # resistant_zone.append(candle2)

            if frequency >= min_touched:
                mean_candle = round(total_candle / frequency, 3)
                resistant_zone.append(candle)

                # for all new resistant, check if the candle is in resistant list, if not add it
                for i in range(len(resistant_zone)):
                    is_resistant = False

                    for j in range(len(resistant_list)):
                        if resistant_zone[i][0] == resistant_list[j][0][0]:
                            # print(f"{resistant_zone[i][0]} = {resistant_list[j][0][0]}")
                            is_resistant = True

                    if not is_resistant:
                        # print(f"{resistant_zone[i][0]} mean_candle = {mean_candle} & frequency = {frequency}")
                        resistant_candle = [resistant_zone[i], mean_candle]
                        resistant_list.append(resistant_candle)

    # print(resistant_list)
    return resistant_list

# H4
# define support level
def define_support_level(df, define_key_level_window = 20):
    # gap
    gap = 0.3

    # all resistant highs
    support_list = []
    
    for row in df.iterrows():
        start_index = row[0] - timedelta(days=define_key_level_window)
        back_candle_range = df.loc[start_index:row[0]]
        pivot_highs = back_candle_range[back_candle_range['is_swing_high'] == True]
        # print(pivot_highs)

        for candle in pivot_highs.iterrows():
            frequency = 0
            total_candle = 0
            # resistant highs related to current high
            support_zone = []

            for candle2 in pivot_highs.iterrows():
                # candle 2 date needs to be before candle date
                if (candle2[0] <= candle[0] and 
                    candle[1]['High'] + gap > candle2[1]['High'] and 
                    candle[1]['High'] - gap < candle2[1]['High']):
                    frequency += 1
                    total_candle += candle2[1]['High']
                    # support_zone.append(candle2)

            if frequency > 2:
                mean_candle = round(total_candle / frequency, 3)
                support_zone.append(candle)

                # for all new resistant, check if the candle is in resistant list, if not add it
                for i in range(len(support_zone)):
                    is_support = False

                    for j in range(len(support_list)):
                        if support_zone[i][0] == support_list[j][0][0]:
                            # print(f"{support_zone[i][0]} = {support_list[j][0][0]}")
                            is_support = True

                    if not is_support:
                        # print(f"{support_zone[i][0]} mean_candle = {mean_candle} & frequency = {frequency}")
                        resistant_candle = [support_zone[i], mean_candle]
                        support_list.append(resistant_candle)

    # print(resistant_list)
    return support_list

# H4
# define support level
def define_support_level_with_atr(df, define_key_level_window = 120, atr_multiplier=0.8, min_touched=3):
    # all resistant highs
    support_list = []
    
    for index in range(len(df)):
        back_candle_range = df.iloc[index-define_key_level_window:index]
        pivot_highs = back_candle_range[back_candle_range['is_swing_high'] == True]
        # print(pivot_highs)

        for candle in pivot_highs.iterrows():
            frequency = 0
            total_candle = 0
            # resistant highs related to current high
            support_zone = []

            for candle2 in pivot_highs.iterrows():
                # candle 2 date needs to be before candle date
                if (candle2[0] <= candle[0] and 
                    candle[1]['High'] + candle[1]['ATR']*atr_multiplier > candle2[1]['High'] and 
                    candle[1]['High'] - candle[1]['ATR']*atr_multiplier < candle2[1]['High']):
                    frequency += 1
                    total_candle += candle2[1]['High']
                    # support_zone.append(candle2)

            if frequency >= min_touched:
                mean_candle = round(total_candle / frequency, 3)
                support_zone.append(candle)

                # for all new resistant, check if the candle is in resistant list, if not add it
                for i in range(len(support_zone)):
                    is_support = False

                    for j in range(len(support_list)):
                        if support_zone[i][0] == support_list[j][0][0]:
                            # print(f"{support_zone[i][0]} = {support_list[j][0][0]}")
                            is_support = True

                    if not is_support:
                        # print(f"{support_zone[i][0]} mean_candle = {mean_candle} & frequency = {frequency}")
                        resistant_candle = [support_zone[i], mean_candle]
                        support_list.append(resistant_candle)

    # print(resistant_list)
    return support_list


def resistant_pos(resistants_list, candle):
    for resistant_pt in resistants_list:
        if candle.name == resistant_pt[0][0]:
            # print(candle)
            return resistant_pt[1]

    return np.nan

def is_resistant(resistants_list, candle):
    for resistant_pt in resistants_list:
        if candle.name == resistant_pt[0][0]:
            # print(candle)
            return True

    return False

def support_pos(supports_list, candle):
    for support_pt in supports_list:
        if candle.name == support_pt[0][0]:
            # print(candle)
            return support_pt[1]

    return np.nan

def is_support(supports_list, candle):
    for support_pt in supports_list:
        if candle.name == support_pt[0][0]:
            # print(candle)
            return True

    return False

# H4 m15
# back candle is the number of day to look back for resistant
# number of day to skip in order to avoid look-ahead
def get_resistant_list(df, current_index, back_candles_window=120, gap=6, tf=TimeFrame.H4):
    if tf == TimeFrame.H4:
        start_date = current_index - back_candles_window
    else:
        start_date = current_index - back_candles_window*16

    end_date = current_index - gap

    window = df.iloc[start_date : end_date]
    resistants_level = window[window['is_resistant'] == True]
    return resistants_level.groupby('resistant_point')['resistant_point'].max()

# H4 m15
# back candle is the number of day to look back for resistant
# number of day to skip in order to avoid look-ahead
def get_support_list(df, current_index, back_candles_window=120, gap=6, tf=TimeFrame.H4):
    if tf == TimeFrame.H4:
        start_date = current_index - back_candles_window
    else:
        start_date = current_index - back_candles_window*16

    end_date = current_index - gap

    window = df.iloc[start_date : end_date]
    supports_level = window[window['is_support'] == True]
    return supports_level.groupby('support_point')['support_point'].max()


# H4
# detect if all candles are below resistant level
def is_candles_below_resistant_level_list(df, breakout_candles=14, key_level_lookback_candle=120):
    valid_resistant_level_list = []

    for index in range(len(df)):
        level_list = []
        resistant_levels_list = get_resistant_list(df, index, key_level_lookback_candle, 6)

        for level in resistant_levels_list:
            if (df['High'].iloc[index-breakout_candles:index] < level).all():
                level_list.append(level)

        valid_resistant_level_list.append(level_list)

    return valid_resistant_level_list

# H4
# detect if all candles are above support level
def is_candles_above_support_level_list(df, breakout_candles=14, key_level_lookback_candle=120):
    valid_support_level_list = []

    for index in range(len(df)):
        level_list = []
        support_levels_list = get_support_list(df, index, key_level_lookback_candle, 6)

        for level in support_levels_list:
            if (df['Low'].iloc[index-breakout_candles:index] > level).all():
                level_list.append(level)

        valid_support_level_list.append(level_list)

    return valid_support_level_list

# apply only in m15 1 H4 candle = 16 m15 candle
def get_valid_breakout_resistant_level(df, index, breakout_candles_below_lookback=25):
    periode = df.iloc[index-1-breakout_candles_below_lookback*16:index-1]
    valid_breakout_resistant_levels = []

    for candle in periode.iterrows():
        if len(candle[1]['valid_breakout_resistant_levels']) > 0:
            for i in range(len(candle[1]['valid_breakout_resistant_levels'])):
                valid_breakout_resistant_levels.append(candle[1]['valid_breakout_resistant_levels'][i])

    return list(set(valid_breakout_resistant_levels))

# apply only in m15 1 H4 candle = 16 m15 candle
def get_valid_resistant_level(df, index, breakout_candles_below_lookback=25):
    periode = df.iloc[index-1-breakout_candles_below_lookback*16:index-1]
    valid_resistant_levels = []

    for candle in periode.iterrows():
        if len(candle[1]['valid_resistant_levels']) > 0:
            for i in range(len(candle[1]['valid_resistant_levels'])):
                valid_resistant_levels.append(candle[1]['valid_resistant_levels'][i])

    return list(set(valid_resistant_levels))

# apply only in m15 1 H4 candle = 16 m15 candle
def get_valid_breakout_support_level(df, index, breakout_candles_above_lookback=25):
    periode = df.iloc[index-1-breakout_candles_above_lookback*16:index-1]
    valid_breakout_support_levels = []

    for candle in periode.iterrows():
        if len(candle[1]['valid_breakout_support_levels']) > 0:
            for i in range(len(candle[1]['valid_breakout_support_levels'])):
                valid_breakout_support_levels.append(candle[1]['valid_breakout_support_levels'][i])

    return list(set(valid_breakout_support_levels))

# apply only in m15 1 H4 candle = 16 m15 candle
def get_valid_support_level(df, index, breakout_candles_above_lookback=25):
    periode = df.iloc[index-1-breakout_candles_above_lookback*16:index-1]
    valid_support_levels = []

    for candle in periode.iterrows():
        if len(candle[1]['valid_support_levels']) > 0:
            for i in range(len(candle[1]['valid_support_levels'])):
                valid_support_levels.append(candle[1]['valid_support_levels'][i])

    return list(set(valid_support_levels))

def pointpos(x):
    if x['TotalSignal']==2:
        return x['Low']-1e-4
    elif x['TotalSignal']==1:
        return x['High']+1e-4
    else:
        return np.nan
