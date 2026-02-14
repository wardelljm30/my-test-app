import streamlit as st
import pandas as pd

st.set_page_config(page_title="Account Mapping Prototype")
st.title("Account Number Mapping Prototype")

st.markdown(
	"Upload a CSV of mappings or edit the sample table below. Any edits will be shown as exceptions (what users updated)."
)

sample = pd.DataFrame(
	{
		"account_id": [1, 2, 3, 4, 5],
		"account_name": [
			"Cash",
			"Receivables",
			"Payables",
			"Equity",
			"Revenue",
		],
		"account_number": ["1000", "1100", "2000", "3000", "4000"],
		"mapped_account_number": ["A100", "A110", "A200", "A300", "A400"],
	}
)

uploaded = st.file_uploader(
	"Upload mappings CSV (columns: account_id, account_name, account_number, mapped_account_number)",
	type="csv",
)

if uploaded is not None:
	try:
		df_orig = pd.read_csv(uploaded)
	except Exception as e:
		st.error(f"Failed to read CSV: {e}")
		st.stop()
else:
	df_orig = sample.copy()

df_orig = df_orig.reset_index(drop=True)

with st.expander("Original (read-only)", expanded=False):
	st.dataframe(df_orig)

st.subheader("Editable Mappings")
edited = st.data_editor(df_orig, num_rows="fixed", use_container_width=True)

# detect rows where any column changed
diff_mask = (df_orig != edited).any(axis=1)
exceptions = edited[diff_mask].copy()

if not exceptions.empty:
	def describe_changes(i):
		changes = []
		for col in df_orig.columns:
			old = df_orig.at[i, col]
			new = edited.at[i, col]
			if pd.isna(old) and pd.isna(new):
				continue
			if old != new:
				changes.append(f"{col}: {old} → {new}")
		return "; ".join(changes) or "(changed)"

	exceptions["changes"] = [describe_changes(i) for i in exceptions.index]
	st.subheader("Exceptions (user updates)")
	st.table(exceptions)
	csv = exceptions.to_csv(index=False)
	st.download_button("Download exceptions CSV", csv, file_name="exceptions.csv", mime="text/csv")
else:
	st.info("No exceptions detected — no user updates found.")

st.sidebar.header("Quick tips")
st.sidebar.markdown("- Edit any cell in the table to create an exception.\n- Upload a CSV to start from your data.")
