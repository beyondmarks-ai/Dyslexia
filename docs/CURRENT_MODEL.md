# Current model pipeline

No model was trained or replaced during the application upgrade. `model.pkl` and `scaler.pkl` remain the production inference artifacts.

## Artifact inspection

| Item | Observed value |
|---|---|
| Model wrapper | `GridSearchCV` |
| Fitted estimator | `RandomForestClassifier` |
| Selected parameters | `n_estimators=100` |
| Search scoring | Accuracy, default 5-fold cross-validation |
| Stored best CV score | 0.92 on the 100-row training partition; not a deployment accuracy claim |
| Serialized scikit-learn version | 1.4.2 |
| Classes | `0`, `1`, `2` |
| Probability support | Yes, via `predict_proba` |
| Feature importance | Yes, global impurity importance from the fitted forest |

The model labels are mapped exactly as in the notebooks and original application:

- `0`: High screening indication
- `1`: Moderate screening indication
- `2`: Low screening indication

These categories are screening outputs, not medical diagnoses.

## Input contract

The scaler was fitted with the following ordered feature names. Every value must be numeric and in the inclusive range 0–1.

1. `Language_vocab`
2. `Memory`
3. `Speed`
4. `Visual_discrimination`
5. `Audio_Discrimination`
6. `Survey_Score`

`services/model_service.py` constructs a DataFrame in this exact order, applies `scaler.pkl`, then calls `model.pkl`. It rejects missing, extra, non-numeric, non-finite and out-of-range values.

Artifact values match the `input_test.ipynb` path: an 80% test split with `random_state=10` leaves 100 rows for fitting `StandardScaler`; its training-column means match the serialized scaler exactly. The grid searches Random Forest sizes 10, 100, 500 and 1000 with `random_state=0`, then serializes the chosen model and scaler. This provenance was inspected only; no training cells were executed.

The original speed formula is retained: `clip(1 - (elapsed_minutes - 3) / (30 - 3), 0, 1)`.

Reading accuracy, reading response time and optional speech metrics are supplementary and are never passed to the model.

The fitted estimator's global impurity importance is: Language vocabulary 0.2712, Speed 0.2510, Memory 0.1918, Visual discrimination 0.1077, Survey score 0.1068, and Audio discrimination 0.0715. These values describe model behavior, not causality.

## Pre-upgrade application status

The original `app.py` could load the artifacts in a compatible scikit-learn environment, but the end-to-end application was technically broken: audio paths pointed to another developer's absolute Windows path, the calculated memory score was never assigned to the model's `Memory` input, and audio submission referenced undefined stress-test variables. The repository also had no dependency manifest. The new service/UI fixes these application issues without changing either artifact.

## Dataset and limitations

`labelled_dysx.csv` has 500 rows, six input columns and one label column. Inputs range from 0 to 1. Label counts are 62 High, 273 Moderate and 165 Low.

### Reproduced held-out evaluation

Without fitting or changing anything, the original `train_test_split(test_size=0.8, random_state=10)` was reconstructed. The 100-row training partition's means exactly matched `scaler.pkl`, confirming that the remaining 400 rows are the artifact-consistent held-out partition. Transforming those rows with the saved scaler and predicting with the saved model produced:

| Metric | Result |
|---|---:|
| Correct predictions | 371 / 400 |
| Accuracy | 92.75% |
| 95% Wilson interval | 89.78%–94.90% |
| Balanced accuracy | 93.81% |
| Macro F1 | 93.07% |
| High-indication recall | 95.83% (46/48) |
| Moderate-indication recall | 91.03% (203/223) |
| Low-indication recall | 94.57% (122/129) |

Confusion matrix (rows are actual High/Moderate/Low; columns are predicted High/Moderate/Low): `[[46, 2, 0], [3, 203, 17], [0, 7, 122]]`.

These figures measure agreement with this repository's labels only. They do not establish clinical sensitivity, specificity, fairness across demographic groups, or real-world diagnostic accuracy. The application must remain a research/educational screening tool.

Pickle files must only be loaded from a trusted source. Their current SHA-256 values are:

- `model.pkl`: `0066D250F35E1865EDBE7DA06DD2CD5F971576BF2A31DC343064357F2873A14C`
- `scaler.pkl`: `CA745840F9CF3F974321BE95FA343C1E549238D65F6FD992F9FB585184F7D726`
