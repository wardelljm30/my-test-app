import streamlit as st
import pandas as pd
import io
import json

st.set_page_config(page_title="Account Mapping Prototype")
st.title("Account Number Mapping Prototype")

st.markdown(
	"Upload a CSV of mappings, manage global mappings, or create client presets. Edits are shown as exceptions."
)

# sample mapping used as initial global mapping
sample = pd.DataFrame(
	{
		"account_id": [1, 2, 3, 4, 5],
		"account_name": ["Cash", "Receivables", "Payables", "Equity", "Revenue"],
		"account_number": ["1000", "1100", "2000", "3000", "4000"],
		"mapped_account_number": ["A100", "A110", "A200", "A300", "A400"],
	}
)

# initialize session state
if "global_map" not in st.session_state:
	st.session_state.global_map = sample.copy()
if "presets" not in st.session_state:
	st.session_state.presets = {}  # name -> {"df": DataFrame, "deliverables": list}
if "deliverables_catalog" not in st.session_state:
	st.session_state.deliverables_catalog = [
		"Delverable 1",
		"Delverable 2",
		"Delverable 3",
		"Delverable 4",
		"Delverable 5"
	]


def df_to_bytes(df):
	return df.to_csv(index=False).encode("utf-8")

def df_from_bytes(b):
	return pd.read_csv(io.BytesIO(b))

# Sidebar: Global mapping management
with st.sidebar.expander("Global mapping (master)", expanded=True):
	st.write("Base mapping used to create new presets.")
	if st.button("Reset global mapping to sample"):
		st.session_state.global_map = sample.copy()
		st.experimental_rerun()

	uploaded_global = st.file_uploader("Import global mapping CSV", type="csv", key="upload_global")
	if uploaded_global is not None:
		try:
			st.session_state.global_map = pd.read_csv(uploaded_global)
			st.success("Imported global mapping.")
		except Exception as e:
			st.error(f"Failed to import: {e}")

	st.download_button(
		"Download global mapping",
		df_to_bytes(st.session_state.global_map),
		file_name="global_mapping.csv",
		mime="text/csv",
	)

	st.data_editor(st.session_state.global_map, key="global_editor", num_rows="fixed", use_container_width=True)

with st.sidebar.expander("Presets & Deliverables", expanded=True):
	st.write("Create, edit, and assign deliverables to client presets.")
	new_preset_name = st.text_input("New preset name")
	if st.button("Create preset from global") and new_preset_name:
		if new_preset_name in st.session_state.presets:
			st.warning("Preset already exists")
		else:
			st.session_state.presets[new_preset_name] = {
				"df": st.session_state.global_map.copy(),
				"deliverables": [],
			}
			st.success(f"Created preset '{new_preset_name}'")

	preset_names = list(st.session_state.presets.keys())
	preset_selected = st.selectbox("Select preset", ["<none>"] + preset_names, index=0)

	if preset_selected != "<none>":
		if st.button("Delete preset"):
			del st.session_state.presets[preset_selected]
			st.experimental_rerun()

		# deliverables assignment
		assigned = st.session_state.presets[preset_selected].get("deliverables", [])
		chosen = st.multiselect(
			"Assign deliverables",
			options=st.session_state.deliverables_catalog,
			default=assigned,
			key=f"deliverables_{preset_selected}",
		)
		st.session_state.presets[preset_selected]["deliverables"] = chosen

		# export/import preset mapping
		st.download_button(
			"Download preset mapping",
			df_to_bytes(st.session_state.presets[preset_selected]["df"]),
			file_name=f"preset_{preset_selected}.csv",
			mime="text/csv",
		)

		up = st.file_uploader("Import preset mapping CSV (replace)", type="csv", key=f"up_preset_{preset_selected}")
		if up is not None:
			try:
				st.session_state.presets[preset_selected]["df"] = pd.read_csv(up)
				st.success("Imported preset mapping.")
			except Exception as e:
				st.error(f"Failed to import preset: {e}")

	if st.button("Export all presets (JSON)"):
		export = {}
		for name, data in st.session_state.presets.items():
			export[name] = {
				"deliverables": data.get("deliverables", []),
				"mapping": data.get("df", pd.DataFrame()).to_dict(orient="list"),
			}
		st.download_button("Download presets JSON", json.dumps(export, indent=2), file_name="presets.json")

# Main area: choose working source (upload / preset / global)
st.subheader("Editable Mappings")
source = st.radio("Choose mapping source:", ["Global", "Preset", "Upload CSV"], index=0)

uploaded = None
if source == "Upload CSV":
	uploaded = st.file_uploader(
		"Upload mappings CSV (columns: account_id, account_name, account_number, mapped_account_number)",
		type="csv",
		key="main_upload",
	)

current_df = None
current_preset_name = None
if source == "Global":
	current_df = st.session_state.global_map.copy()
elif source == "Preset":
	preset_choice = st.selectbox("Choose preset to edit", ["<none>"] + list(st.session_state.presets.keys()))
	if preset_choice != "<none>":
		current_df = st.session_state.presets[preset_choice]["df"].copy()
		current_preset_name = preset_choice
	else:
		st.info("No preset selected — choose one from the dropdown.")
elif source == "Upload CSV" and uploaded is not None:
	try:
		current_df = pd.read_csv(uploaded)
	except Exception as e:
		st.error(f"Failed to read CSV: {e}")

if current_df is None:
	st.stop()

current_df = current_df.reset_index(drop=True)

with st.expander("Original (read-only)", expanded=False):
	st.dataframe(current_df)

edited = st.data_editor(current_df, num_rows="fixed", use_container_width=True)

# detect rows where any column changed
diff_mask = (current_df != edited).any(axis=1)
exceptions = edited[diff_mask].copy()

if not exceptions.empty:
	def describe_changes(i):
		changes = []
		for col in current_df.columns:
			old = current_df.at[i, col]
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

# If editing a preset, offer to save changes back to the preset
if current_preset_name:
	if st.button("Save changes to preset"):
		st.session_state.presets[current_preset_name]["df"] = edited.copy()
		st.success(f"Saved changes to preset '{current_preset_name}'")

st.sidebar.header("Quick tips")
st.sidebar.markdown("- Edit any cell in the table to create an exception.\n- Use the sidebar to manage global mapping and presets.")
