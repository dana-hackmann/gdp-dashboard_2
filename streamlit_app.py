import streamlit as st
import pandas as pd
from io import StringIO
from urllib.request import urlopen

DATA_URL = (
    'https://berkeley-earth-temperature.s3.us-west-1.amazonaws.com/Global/'
    'Land_and_Ocean_complete.txt'
)

COLUMN_NAMES = [
    'Year',
    'Month',
    'Monthly Anomaly',
    'Monthly Unc',
    'Annual Anomaly',
    'Annual Unc',
    'Five-year Anomaly',
    'Five-year Unc',
    'Ten-year Anomaly',
    'Ten-year Unc',
    'Twenty-year Anomaly',
    'Twenty-year Unc',
]

SECTION_LABELS = {
    'Air Temperatures': (
        'Global Average Temperature Anomaly with Sea Ice Temperature '
        'Inferred from Air Temperatures'
    ),
    'Water Temperatures': (
        'Global Average Temperature Anomaly with Sea Ice Temperature '
        'Inferred from Water Temperatures'
    ),
}


@st.cache_data
def load_berkeley_temperatures(url: str = DATA_URL):
    with urlopen(url) as response:
        raw_text = response.read().decode('utf-8')

    lines = raw_text.splitlines()
    section_data = {label: [] for label in SECTION_LABELS}
    active_section = None

    for line in lines:
        if line.startswith('%'):
            stripped = line.lstrip('%').strip()
            if stripped in SECTION_LABELS.values():
                active_section = next(
                    label for label, value in SECTION_LABELS.items() if value == stripped
                )
            continue

        if active_section and line.strip():
            section_data[active_section].append(line)

    parsed = {}
    for label, rows in section_data.items():
        if not rows:
            continue

        section_text = '\n'.join(rows)
        df = pd.read_csv(
            StringIO(section_text),
            sep=r'\s+',
            header=None,
            names=COLUMN_NAMES,
            na_values=['NaN'],
            engine='python',
        )
        df['Date'] = pd.to_datetime(
            df['Year'].astype(int).astype(str)
            + '-'
            + df['Month'].astype(int).astype(str)
            + '-01'
        )
        parsed[label] = df

    return parsed


st.set_page_config(
    page_title='Berkeley Earth Temperature Dashboard',
    page_icon=':thermometer:',
)

st.title('Berkeley Earth Land + Ocean Temperature Explorer')
st.markdown(
    'This app loads the Berkeley Earth global land-and-ocean temperature anomaly '
    'dataset directly from the public text file and visualizes monthly and '
    'rolling-average anomalies.'
)

all_data = load_berkeley_temperatures()
selected_section = st.selectbox('Choose the temperature series', list(all_data))

df = all_data[selected_section]

# ---------------------------------------------------------
# ⭐ Rolling Means hinzufügen
# ---------------------------------------------------------
df['Rolling 12M'] = df['Monthly Anomaly'].rolling(window=12).mean()
df['Rolling 60M'] = df['Monthly Anomaly'].rolling(window=60).mean()
df['Rolling 120M'] = df['Monthly Anomaly'].rolling(window=120).mean()
# ---------------------------------------------------------

min_year = int(df['Year'].min())
max_year = int(df['Year'].max())

# Standardmäßig ab 1900 oder dem frühesten Jahr
default_start_year = max(1900, min_year)

selected_years = st.slider(
    'Select year range',
    min_value=min_year,
    max_value=max_year,
    value=(default_start_year, max_year),
    help='Filter the dataset by the year range shown in the chart.',
)

filtered_df = df[(df['Year'] >= selected_years[0]) & (df['Year'] <= selected_years[1])]

if filtered_df.empty:
    st.warning('No data is available for the chosen year range.')
else:
    st.subheader('Global Temperature Anomalies')
    st.line_chart(
        filtered_df.set_index('Date')[
            [
                'Monthly Anomaly',
                'Annual Anomaly',
                'Five-year Anomaly',
                'Ten-year Anomaly',
                'Twenty-year Anomaly',
                'Rolling 12M',
                'Rolling 60M',
                'Rolling 120M',
            ]
        ]
    )

    latest = filtered_df.iloc[-1]
    earliest = filtered_df.iloc[0]

    st.metric(
        label='Latest monthly anomaly',
        value=f"{latest['Monthly Anomaly']:.3f} °C",
        delta=f"{latest['Monthly Anomaly'] - earliest['Monthly Anomaly']:+.3f} °C",
    )
    st.metric(
        label='Latest annual anomaly',
        value=f"{latest['Annual Anomaly']:.3f} °C",
        delta=f"{latest['Annual Anomaly'] - earliest['Annual Anomaly']:+.3f} °C",
    )

    st.markdown('### Recent data sample')
    st.dataframe(
        filtered_df[
            [
                'Date',
                'Monthly Anomaly',
                'Annual Anomaly',
                'Five-year Anomaly',
                'Ten-year Anomaly',
                'Rolling 12M',
                'Rolling 60M',
                'Rolling 120M',
            ]
        ].tail(15),
        width='stretch',
    )
