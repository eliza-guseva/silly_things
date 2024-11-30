import streamlit as st
import datetime
import calendar
import os
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

# This will load from .env locally and from Streamlit secrets in production
load_dotenv()

AMOUNT = float(os.getenv('AMOUNT', 1000))
SECRET_CODE = os.getenv('SECRET_CODE', 'default_code')

def calculate_daily_rate(amount: float, selected_date=None) -> float:
    """Calculate how much money is allocated per day"""
    date = selected_date if selected_date else datetime.date.today()
    days_in_month = calendar.monthrange(date.year, date.month)[1]
    return amount / days_in_month

def calculate_accumulated_amount(daily_rate, selected_date=None):
    """Calculate how much money should be accumulated until today"""
    date = selected_date if selected_date else datetime.date.today()
    return daily_rate * date.day

def get_current_file_name(selected_date=None):
    """Generate file name based on selected month and year, or current month if none selected"""
    date = selected_date if selected_date else datetime.date.today()
    return f"{date.strftime('%B').lower()}_{date.year}.csv"

def load_spent_money(selected_date=None):
    """Load spent money from CSV file"""
    file_name = get_current_file_name(selected_date)
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        df['date'] = pd.to_datetime(df['date'])  # Convert date column to datetime
        return df
    return pd.DataFrame(columns=['date', 'amount'])  # Return empty DataFrame if file doesn't exist

def save_expense(amount, date):
    """Save new expense to CSV file"""
    file_name = get_current_file_name()
    new_expense = pd.DataFrame({
        'date': [date],
        'amount': [amount]
    })
    
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        df = pd.concat([df, new_expense], ignore_index=True)
    else:
        df = new_expense
    df.to_csv(file_name, index=False)


# Add month selector
today = datetime.date.today()
first_possible_date = today.replace(year=today.year-1, month=1, day=1)  # Allow selecting up to 1 year back
selected_month = st.date_input(
    "Select Month:",
    value=today,
    min_value=first_possible_date,
    max_value=today
)
# Normalize selected date to first of month
selected_month = selected_month.replace(day=1)

# Initialize session state for spent money from file
if 'spent_money' not in st.session_state or 'current_month' not in st.session_state or st.session_state.current_month != selected_month:
    df = load_spent_money(selected_month)
    st.session_state.spent_money = df['amount'].sum()
    st.session_state.current_month = selected_month

st.title("Mystery Budget")

# Calculate daily rate and accumulated amount for selected month
daily_rate = calculate_daily_rate(AMOUNT, selected_month)
accumulated = calculate_accumulated_amount(daily_rate, selected_month)
remainder = AMOUNT - st.session_state.spent_money

# Display current budget status
st.header("Budget Status")
col1, col2 = st.columns(2)
with col1:
    st.metric(
        label="Money Spent",
        value=f"${st.session_state.spent_money:.2f}"
    )
with col2:
    st.metric(
        label="Remaining Budget",
        value=f"${remainder:.2f}",
        delta=f"${remainder:.2f}",
        delta_color="inverse"
    )

# Input for spending money
col1, col2 = st.columns(1)  # First row with two columns
with col1:
    spent = st.number_input("Enter amount spent:", min_value=0.0, value=0.0, step=0.1)
with col2:
    # Get the first and last day of current month
    today = datetime.date.today()
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    expense_date = st.date_input(
        "Date:",
        value=today,
        min_value=first_day,
        max_value=last_day
    )

# Second row with button and secret code
button_col, code_col = st.columns([1, 1])  # Equal width columns
with code_col:
    entered_code = st.text_input("Secret Code:", type="password")
with button_col:
    if st.button("Record Expense"):
        if entered_code == SECRET_CODE:
            st.session_state.spent_money += spent
            save_expense(spent, expense_date)
            st.rerun()
        else:
            st.error("Invalid secret code")

# Add spending visualization
st.header("Spending Visualization")
df = load_spent_money(selected_month)
if not df.empty:
    # Sort by date and calculate cumulative sum
    df = df.sort_values('date')
    df['cumulative_spent'] = df['amount'].cumsum()
    
    # Create a date range for the ideal spending line
    date_range = pd.date_range(start=df['date'].min(), end=selected_month.replace(day=calendar.monthrange(selected_month.year, selected_month.month)[1]))
    
    # Create ideal spending DataFrame
    ideal_df = pd.DataFrame({
        'date': date_range,
        'ideal_spending': [daily_rate * (i + 1) for i in range(len(date_range))]
    })
    
    # Merge actual and ideal spending
    plot_df = pd.merge(
        ideal_df, 
        df.groupby('date')['cumulative_spent'].last().reset_index(), 
        on='date', 
        how='left',
    )
    plot_df = plot_df.fillna(method='ffill')
    
    # Create the line chart
    fig = px.line(plot_df, x='date', 
                  y=['ideal_spending', 'cumulative_spent'],
                  line_shape='linear')
    
    fig.update_traces(line=dict(width=4))  # Make lines thicker
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No spending data available yet.")


