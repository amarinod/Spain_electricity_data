import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button, CheckButtons, Slider, RadioButtons
import time
import os
import platform
from pandas import ExcelWriter

# === Load Data ===
price_path = "UNSURE_Spain_Prices_DataSet.csv"
price_df = pd.read_csv(price_path)
if 'value' not in price_df.columns and len(price_df.columns) >= 2:
    price_df.rename(columns={price_df.columns[-1]: 'value'}, inplace=True)
price_df['datetime'] = pd.to_datetime(price_df['datetime'], utc=True, errors='coerce')
price_df = price_df.dropna(subset=['datetime'])
price_df['hour'] = price_df['datetime'].dt.hour
price_df['month'] = price_df['datetime'].dt.month
price_df['year'] = price_df['datetime'].dt.year.astype(int)

future_df = pd.read_csv("Prediction_Spain_prices_dataset.csv", header=None)
future_df.columns = ['datetime', 'value']
future_df['datetime'] = pd.to_datetime(future_df['datetime'], errors='coerce')
future_df = future_df.dropna(subset=['datetime'])
future_df['hour'] = future_df['datetime'].dt.hour
future_df['month'] = future_df['datetime'].dt.month
future_df['year'] = future_df['datetime'].dt.year.astype(int)
future_df['dayofweek'] = future_df['datetime'].dt.dayofweek



def load_and_prepare(filepath):
    df = pd.read_csv(filepath, header=0, skiprows=[1, 2])
    df = df[['date', 'E_Grid']].dropna()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['E_Grid'] = pd.to_numeric(df['E_Grid'], errors='coerce')
    df = df.dropna()
    df['month'] = df['date'].dt.month
    df['hour'] = df['date'].dt.hour
    return df

df_vc1 = load_and_prepare("CLIPPING EXAMPLE4_Project_VC1_HourlyRes_0.CSV")
df_vc2 = load_and_prepare("CLIPPING EXAMPLE5_Project_VC2_HourlyRes_0.CSV")
df_vc3 = load_and_prepare("CLIPPING EXAMPLE6_Project_VC3_HourlyRes_0.CSV")
vc_data = {"VC1": df_vc1, "VC2": df_vc2, "VC3": df_vc3}

vc_dow_profiles = {
    label: df.groupby(df['date'].dt.dayofweek)['E_Grid'].mean().reindex(range(7), fill_value=0)
    for label, df in vc_data.items()
}

static_egrid_hourly = pd.concat([
    df.groupby('hour')['E_Grid'].mean() for df in vc_data.values()
], axis=1).mean(axis=1)

static_egrid_monthly = pd.concat([
    df.groupby('month')['E_Grid'].mean() for df in vc_data.values()
], axis=1).mean(axis=1)

month_names = {i: name for i, name in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
selected_months = set(range(1, 13))
visible_vcs = set(["VC1", "VC2", "VC3"])

def compute_capture_factors_by_year():
    years, values = [], []
    for year in range(2015, 2026):
        df_year = price_df[price_df['year'] == year]
        avg_price_hourly = df_year.groupby('hour')['value'].mean()
        common_hours = avg_price_hourly.index.intersection(static_egrid_hourly.index)
        if not common_hours.empty:
            weighted = (avg_price_hourly[common_hours] * static_egrid_hourly[common_hours]).sum()
            total_egrid = static_egrid_hourly[common_hours].sum()
            avg_price = avg_price_hourly[common_hours].mean()
            if total_egrid > 0 and avg_price > 0:
                capture = (weighted / total_egrid) / avg_price
                years.append(year)
                values.append(capture)
    return years, values

capture_years_static, capture_values_static = compute_capture_factors_by_year()

current_tab = 'Hourly View'

apply_inflation = False


# GUI Setup with Improved Layout
fig = plt.figure(figsize=(14, 8))  # Increased figure size
gs = gridspec.GridSpec(4, 7, width_ratios=[2.8, 1, 1, 1, 1, 1, 1], height_ratios=[0.08, 3.5, 1, 3.5])


# Main plot spans row 1 (index 1) and columns 1 to 5
ax1 = plt.subplot(gs[1, 1:7])
# Capture factor plot spans row 2 (index 2) and columns 1 to 5
ax2 = plt.subplot(gs[3, 1:7])
# Secondary y-axis
ax1b = ax1.twinx()


# Sliders
slider_ax1 = plt.axes([0.3, 0.93, 0.6, 0.025])
slider_ax2 = plt.axes([0.3, 0.89, 0.6, 0.025])
slider_start = Slider(slider_ax1, 'Start Year', 2015, 2025, valinit=2015, valstep=1)
slider_end = Slider(slider_ax2, 'End Year', 2015, 2025, valinit=2025, valstep=1)

# Month Checkboxes
rax_month = plt.axes([0.03, 0.5, 0.15, 0.4])  # Left column, middle
labels_month = [month_names[m] for m in range(1, 13)]
checks = CheckButtons(rax_month, labels_month, [True]*12)

# VC Checkboxes
rax_vc = plt.axes([0.05, 0.1, 0.2, 0.20])  # Below month checkboxes
vc_labels = ['VC1', 'VC2', 'VC3']
vc_checks = CheckButtons(rax_vc, vc_labels, [True]*3)

tab_ax = plt.axes([0.20, 0.6, 0.12, 0.2])  # To the right of month checkboxes
tab_buttons = RadioButtons(tab_ax, ['Hourly View', 'Monthly View', 'Day of Week View'], active=0)
def change_tab(label):
    global current_tab
    current_tab = label
    update_plot(None)

# Register the callback
tab_buttons.on_clicked(change_tab)

# Excel Button
excel_ax = plt.axes([0.05, 0.03, 0.15, 0.05])  # Bottom left
excel_button = Button(excel_ax, 'Export to Excel', color='lightgray', hovercolor='0.975')

#Sellect all button
select_ax = plt.axes([0.03, 0.44, 0.15, 0.05])
select_button = Button(select_ax, 'Select all', color='lightgray', hovercolor='0.95')

deselect_ax = plt.axes([0.03, 0.38, 0.15, 0.05])
deselect_button = Button(deselect_ax, 'Deselect all', color='lightgray', hovercolor='0.95')

#past or future buttons
data_radio_ax = plt.axes([0.20, 0.38, 0.10, 0.08])  # Adjust position as needed
data_radio = RadioButtons(data_radio_ax, ['Past', 'Future'], active=0)

#2% inflation
inflation_ax = plt.axes([0.20, 0.48, 0.10, 0.05])
inflation_button = Button(inflation_ax, 'Apply 2% Inflation', color='lightgray', hovercolor='0.95')

def select_all_months(event):
    for i in range(12):
        if not checks.get_status()[i]:
            checks.set_active(i)
    update_plot(None)

def deselect_all_months(event):
    for i in range(12):
        if checks.get_status()[i]:
            checks.set_active(i)
    update_plot(None)

def update_plot(val):
    

    df = price_df if data_radio.value_selected == 'Past' else future_df
    if data_radio.value_selected == 'Future' and apply_inflation:
        df = df.copy()
        df['value'] *= (1.02) ** (df['year'] - 2025)

    if 'year' not in df.columns:
        df['year'] = df['datetime'].dt.year.astype(int)
    if 'month' not in df.columns:
        df['month'] = df['datetime'].dt.month
    print("df columns:", df.columns)
    global current_tab
    start_time = time.time()
    ax1.clear()
    ax1b.clear()
    ax2.clear()

    start, end = int(slider_start.val), int(slider_end.val)
    filtered_prices = df[
        (df['year'] >= start) &
        (df['year'] <= end) &
        (df['month'].isin(selected_months))
    ]


    active_vcs = [vc_data[label] for label in visible_vcs]
    dynamic_values = []
    
    if current_tab == 'Hourly View':
        hourly_price = filtered_prices.groupby('hour')['value'].mean()

        if active_vcs:
            dynamic_egrid_hourly = pd.concat([
                vc_df[vc_df['month'].isin(selected_months)].groupby('hour')['E_Grid'].mean()
                for vc_df in active_vcs
            ], axis=1).mean(axis=1)
        else:
            dynamic_egrid_hourly = pd.Series(dtype=float)

        ax1.plot(hourly_price.index, hourly_price.values, label="Price", color='black', marker='o')
        if not hourly_price.empty:
            avg_price = hourly_price.mean()
            ax1.axhline(avg_price, color='red', linestyle='--', label=f"Avg Price: {avg_price:.1f}")

            common_hours = hourly_price.index.intersection(dynamic_egrid_hourly.index)
            if not common_hours.empty:
                weighted = (hourly_price[common_hours] * dynamic_egrid_hourly[common_hours]).sum()
                total_egrid = dynamic_egrid_hourly[common_hours].sum()
                if total_egrid > 0:
                    w_avg = weighted / total_egrid
                    ax1.axhline(w_avg, linestyle='--', color='blue', label=f"Weighted Avg: {w_avg:.2f}")

        morning = hourly_price.loc[hourly_price.index < 12]
        afternoon = hourly_price.loc[hourly_price.index >= 12]
        if not morning.empty:
            min_hour_m = morning.idxmin()
            morning_high = morning[morning.index > min_hour_m]
            if not morning_high.empty:
                max_hour_m = morning_high.idxmax()
                ax1.annotate(f"Min (AM): {morning[min_hour_m]:.1f}", xy=(min_hour_m, morning[min_hour_m]), xytext=(min_hour_m, morning[min_hour_m] - 3), ha='center', fontsize=8)
                ax1.annotate(f"Max (AM): {morning[max_hour_m]:.1f}", xy=(max_hour_m, morning[max_hour_m]), xytext=(max_hour_m, morning[max_hour_m] + 3), ha='center', fontsize=8)
        if not afternoon.empty:
            min_hour_p = afternoon.idxmin()
            afternoon_high = afternoon[afternoon.index > min_hour_p]
            if not afternoon_high.empty:
                max_hour_p = afternoon_high.idxmax()
                ax1.annotate(f"Min (PM): {afternoon[min_hour_p]:.1f}", xy=(min_hour_p, afternoon[min_hour_p]), xytext=(min_hour_p, afternoon[min_hour_p] - 3), ha='center', fontsize=8)
                ax1.annotate(f"Max (PM): {afternoon[max_hour_p]:.1f}", xy=(max_hour_p, afternoon[max_hour_p]), xytext=(max_hour_p, afternoon[max_hour_p] + 6), ha='center', fontsize=8)

        for label, vc_df in vc_data.items():
            if label not in visible_vcs:
                continue
            df_filt = vc_df[vc_df['month'].isin(selected_months)]
            avg_hourly = df_filt.groupby('hour')['E_Grid'].mean()
            ax1b.fill_between(avg_hourly.index, 0, avg_hourly.values, alpha=0.25, label=label)

        dynamic_values = []

        for year in range(start, end + 1):
            df_year = df[(df['year'] == year) & (df['month'].isin(selected_months))]
            if df_year.empty or not active_vcs:
                continue

            avg_price_hourly = df_year.groupby('hour')['value'].mean()
            if avg_price_hourly.empty:
                continue

            hourly_egrid = pd.concat([
                vc_df[vc_df['month'].isin(selected_months)].groupby('hour')['E_Grid'].mean()
                for vc_df in active_vcs
            ], axis=1).mean(axis=1)

            common_hours = avg_price_hourly.index.intersection(hourly_egrid.index)
            if not common_hours.empty:
                weighted = (avg_price_hourly[common_hours] * hourly_egrid[common_hours]).sum()
                total_egrid = hourly_egrid[common_hours].sum()
                avg_price = avg_price_hourly[common_hours].mean()
                if total_egrid > 0 and avg_price > 0:
                    capture_factor = (weighted / total_egrid) / avg_price
                    dynamic_values.append((year, capture_factor))

        if dynamic_values:
            ys, vs = zip(*dynamic_values)
            ax2.plot(ys, vs, marker='o', color='purple')
            ax2.set_title("Capture Factor by Year")
            ax2.set_xlabel("Year")
            ax2.set_ylabel("Capture Factor")
            ax2.set_xlim(min(ys)-1, max(ys)+1)
            ax2.set_xticks(range(min(ys), max(ys)+1))
            ax2.set_xticklabels(range(min(ys), max(ys)+1), rotation=45)
            ax2.set_ylim(0.3, 1.3)
            ax2.grid(True, linestyle='--', alpha=0.5)
        else:
            ax2.text(0.5, 0.5, 'No capture factor data', transform=ax2.transAxes,
                 ha='center', va='center', fontsize=12, color='gray')


    elif current_tab == 'Monthly View':
        monthly_price = filtered_prices.groupby('month')['value'].mean()
        ax1.plot(monthly_price.index, monthly_price.values, label="Price", color='black', marker='o')

        for label, df in vc_data.items():
            if label not in visible_vcs:
                continue
            df_filt = df[df['month'].isin(selected_months)]
            avg_monthly = df_filt.groupby('month')['E_Grid'].mean()
            ax1b.fill_between(avg_monthly.index, avg_monthly.values, alpha=0.25, label=label)

        capture_monthly = []
        for m in range(1, 13):
            if m not in selected_months:
                continue
            month_prices = filtered_prices[filtered_prices['month'] == m]
            hourly_price = month_prices.groupby('hour')['value'].mean()
            if active_vcs:
                hourly_egrid = pd.concat([
                    df[df['month'] == m].groupby('hour')['E_Grid'].mean() for df in active_vcs
                ], axis=1).mean(axis=1)
            else:
                continue
            common_hours = hourly_price.index.intersection(hourly_egrid.index)
            if not common_hours.empty:
                weighted_sum = (hourly_price[common_hours] * hourly_egrid[common_hours]).sum()
                total_egrid = hourly_egrid[common_hours].sum()
                avg_price = hourly_price[common_hours].mean()
                if total_egrid > 0 and avg_price > 0:
                    captured_price = weighted_sum / total_egrid
                    capture_factor = captured_price / avg_price
                    capture_monthly.append((m, capture_factor))

        common_months = monthly_price.index.intersection(static_egrid_monthly.index)
        if not common_months.empty:
            weighted = (monthly_price[common_months] * static_egrid_monthly[common_months]).sum()
            total_egrid = static_egrid_monthly[common_months].sum()
            if total_egrid > 0:
                w_avg = weighted / total_egrid
                ax1.axhline(w_avg, linestyle='--', color='blue', label=f"Weighted Avg: {w_avg:.2f}")

        if capture_monthly:
            ms, cs = zip(*capture_monthly)
            ax2.plot(ms, cs, marker='o', color='teal')
            ymin = max(0.3, min(cs) - 0.05)
            ymax = min(1.3, max(cs) + 0.05)
            ax1.set_title("Electricity Price Curve and VC Capture Potential by Month")
            ax2.set_ylim(ymin, ymax)
            ax2.set_title("Capture Factor by Month")
            ax2.set_ylabel("Capture Factor")
            ax2.set_xlabel("Month")
            ax2.set_xticks(range(1, 13))
            ax2.set_xticklabels([month_names[m] for m in range(1, 13)], rotation=45)

    elif current_tab == 'Day of Week View':
        dow_price = filtered_prices.groupby(filtered_prices['datetime'].dt.dayofweek)['value'].mean()
        avg_price = dow_price.mean()
        ax1.plot(dow_price.index, dow_price.values, label="Price", color='black', marker='o')
        ax1.axhline(avg_price, color='red', linestyle='--', label=f"Avg Price: {avg_price:.2f}")

        vc_dow_data = {}
        for label in visible_vcs:
            df_dow = vc_dow_profiles.get(label)
            if df_dow is None or df_dow.empty:
                continue
            df_dow = df_dow.dropna().sort_index()
            if all(i in df_dow.index for i in range(7)):
                ax1b.fill_between(df_dow.index, 0, df_dow.values, alpha=0.15, label=label)
                vc_dow_data[label] = df_dow

        if vc_dow_data:
            avg_dow_egrid = pd.concat(vc_dow_data.values(), axis=1).mean(axis=1)
            common_dow = dow_price.index.intersection(avg_dow_egrid.index)
            weighted = (dow_price[common_dow] * avg_dow_egrid[common_dow]).sum()
            total_egrid = avg_dow_egrid[common_dow].sum()
            if total_egrid > 0:
                w_avg = weighted / total_egrid
                ax1.axhline(w_avg, linestyle='--', color='blue', label=f"Weighted Avg: {w_avg:.2f}")
            if total_egrid > 0 and avg_price > 0:
                #capture_dow = (weighted / total_egrid) / avg_price
                capture_dow = (dow_price[common_dow] / avg_price)
                ax2.plot(common_dow, capture_dow, marker='o', color='purple')
                ax1.set_title("Electricity Price Curve and VC Capture Potential by Day of Week")
                ax2.set_title("Capture Factor by Day of Week")
                ax2.set_ylabel("Capture Factor")
                ax2.set_xlabel("Day of Week")
                ax2.set_ylim(0.7, 1.3)
                ax2.set_xticks(range(7))
                ax2.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1b.get_legend_handles_labels()
    ax1b.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    fig.canvas.draw_idle()
    print(f"update_plot completed in {time.time() - start_time:.2f} sec")

def update_months(label):
    global selected_months
    month = list(month_names.keys())[list(month_names.values()).index(label)]
    if month in selected_months:
        selected_months.remove(month)
    else:
        selected_months.add(month)
    update_plot(None)

def change_tab(label):
    global current_tab
    current_tab = label
    update_plot(None)

def update_vc_visibility(label):
    global visible_vcs
    if label in visible_vcs:
        visible_vcs.remove(label)
    else:
        visible_vcs.add(label)
    update_plot(None)

def toggle_inflation(event):
    global apply_inflation
    apply_inflation = not apply_inflation
    inflation_button.label.set_text("Inflation: ON" if apply_inflation else "Inflation: OFF")
    update_plot(None)

def export_to_excel(event):
    start, end = int(slider_start.val), int(slider_end.val)
    filtered_prices = price_df[
        (price_df['year'] >= start) &
        (price_df['year'] <= end) &
        (price_df['month'].isin(selected_months))
    ]
    start_date = pd.to_datetime(f"{start}-01-01")
    end_date = pd.to_datetime(f"{end}-12-31")
    all_days = pd.date_range(start=start_date, end=end_date, freq='D')
    full_timestamps = [pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=h) 
                      for day in all_days for h in range(24)]

    df_export = pd.DataFrame({
        "DateTime": full_timestamps,
        "Date": [dt.date() for dt in full_timestamps],
        "Hour": [dt.hour for dt in full_timestamps]
    })

    temp_prices = filtered_prices.copy()
    temp_prices['datetime'] = pd.to_datetime(temp_prices['datetime'], utc=True).dt.tz_localize(None)
    temp_prices['rounded_datetime'] = temp_prices['datetime'].dt.floor('H')

    merged = pd.merge(
        df_export,
        temp_prices[['rounded_datetime', 'value']],
        left_on='DateTime',
        right_on='rounded_datetime',
        how='left'
    ).drop(columns=['rounded_datetime'])

    merged.rename(columns={"value": "Price"}, inplace=True)

    for label in visible_vcs:
        vc_profile = vc_data[label].copy()
        vc_profile['hour'] = vc_profile['date'].dt.hour
        avg_hourly = vc_profile.groupby('hour')['E_Grid'].mean()
        merged[f"E_Grid_{label}"] = merged['Hour'].map(avg_hourly)
        merged[f"Revenue_{label}"] = merged[f"E_Grid_{label}"] * merged["Price"]

    merged["Year"] = merged["DateTime"].dt.year
    merged["Captured Price"] = ""
    merged["Baseload"] = ""
    merged["Captured Factor"] = ""

    for y in range(start, end + 1):
        yearly_data = merged[merged["Year"] == y]
        if yearly_data.empty:
            continue
        for label in visible_vcs:
            revenue_sum = yearly_data[f"Revenue_{label}"].sum()
            egrid_sum = yearly_data[f"E_Grid_{label}"].sum()
            avg_price = yearly_data["Price"].mean(skipna=True)
            if egrid_sum > 0 and avg_price > 0:
                captured_price = revenue_sum / egrid_sum
                captured_factor = captured_price / avg_price
                first_idx = yearly_data.index[0]
                merged.at[first_idx, f"Captured Price {label}"] = captured_price
                merged.at[first_idx, f"Baseload {label}"] = avg_price
                merged.at[first_idx, f"Captured Factor {label}"] = f"{captured_factor:.2%}"

    file_path = "Spain_energy_data.xlsx"
    merged.to_excel(file_path, index=False)
    print(f"✅ Excel saved as {file_path}")

    if platform.system() == "Darwin":
        os.system(f"open {file_path}")
    elif platform.system() == "Windows":
        os.startfile(file_path)
    else:
        os.system(f"xdg-open {file_path}")

# Connect callbacks
checks.on_clicked(update_months)
slider_start.on_changed(update_plot)
slider_end.on_changed(update_plot)
tab_buttons.on_clicked(change_tab)
vc_checks.on_clicked(update_vc_visibility)
excel_button.on_clicked(export_to_excel)
select_button.on_clicked(select_all_months)
deselect_button.on_clicked(deselect_all_months)
data_radio.on_clicked(lambda _: update_plot(None))
inflation_button.on_clicked(toggle_inflation)

def update_data_source(label):
    if label == 'Past':
        years = price_df['year'].dropna().unique()
    else:
        years = future_df['year'].dropna().unique()

    min_year = int(years.min())
    max_year = int(years.max())

    # Update slider range and values
    slider_start.valmin = min_year
    slider_start.valmax = max_year
    slider_start.ax.set_xlim(min_year, max_year)
    slider_start.set_val(min_year)

    slider_end.valmin = min_year
    slider_end.valmax = max_year
    slider_end.ax.set_xlim(min_year, max_year)
    slider_end.set_val(max_year)

    update_plot(None)

data_radio.on_clicked(update_data_source)



update_plot(None)
plt.show()