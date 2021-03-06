import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


class EDA:

    def __init__(self, df):
        self.df = df


class CleanData(EDA):

    def missing_report(self, pct_threshold=0):
        missing_vals_n = self.df.isna().sum().sort_values(ascending=False)
        missing_vals_pct = round(missing_vals_n / self.df.shape[0], 3)

        missing_vals = pd.concat([missing_vals_n, missing_vals_pct], axis=1, keys=['n', 'pct'])

        return missing_vals[missing_vals['pct'] > pct_threshold]

    def outlier_report(self, pct_threshold=0):
        df_numeric = self.df.select_dtypes(['int', 'float']).copy()
        outliers = df_numeric.apply(lambda x: np.abs(x - x.mean()) / x.std() < 3)  # .all(axis=1).value_counts()

        n_outliers = pd.melt(outliers.apply(pd.Series.value_counts).iloc[[0]])
        n_outliers['pct_outliers'] = round(n_outliers['value'] / self.df.shape[0], 2)
        n_outliers_ordered = n_outliers.dropna().sort_values('value', ascending=False)

        return n_outliers_ordered[n_outliers_ordered['pct_outliers'] > pct_threshold]

    def handle_missing_values(self, drop_vars=None):
        if drop_vars is None:
            drop_vars = []
        else:
            drop_vars = drop_vars

        df_clean = self.df.copy()
        df_clean.drop(drop_vars, inplace=True, axis=1)
        df_clean.dropna(inplace=True)

        return df_clean

    def handle_outlier_values(self, drop_vars=None):
        """Detect outliers that are 3 std away from mean (1% highest and lowest)"""
        if drop_vars is None:
            drop_vars = []
        else:
            drop_vars = drop_vars

        df_clean = self.df.select_dtypes(['int', 'float']).copy()
        df_clean.drop(drop_vars, inplace=True, axis=1)
        detect_outliers = df_clean.apply(lambda x: np.abs(x - x.mean()) / x.std() < 3).all(axis=1)

        self.df.drop(drop_vars, inplace=True, axis=1)
        print(detect_outliers.value_counts())

        return self.df[detect_outliers]

    def normalize(self):
        result = self.df.copy()
        for feature_name in self.df.select_dtypes(['int', 'float']).columns:
            max_value = self.df[feature_name].max()
            min_value = self.df[feature_name].min()
            result[feature_name] = (self.df[feature_name] - min_value) / (max_value - min_value)
        return result


class ExploreVis(EDA):

    def __init__(self, df, save_fig=False, output_path=None):
        super().__init__(df)
        self.save_fig = save_fig
        self.output_path = output_path

    def _save_fig(self):
        """save plots to specified output location"""
        if self.save_fig is True:
            if self.output_path is None:
                raise ValueError('Need to specify output path to save the plot')
            else:
                plt.savefig(self.output_path, bbox_inches='tight')

    def plt_feature_distribution(self, chart_height):
        order = pd.melt(self.df.select_dtypes(['int', 'float'])).groupby('variable')['value'].mean().sort_values()[
                ::-1].index

        plt.figure(figsize=(14, chart_height))
        sns.boxplot(x="value", y="variable", data=pd.melt(self.df.select_dtypes(['int', 'float'])), order=order,
                    fliersize=0.5, palette='viridis')

        plt.xlabel('')
        plt.ylabel('')
        plt.title('Feature Set Distribution')

        self._save_fig()
        return plt.show()

    def feature_delta_by_target(self, target_var, metric, top_n, drop_vars=None):

        if metric not in ['mean', 'median']:
            raise ValueError('Available metrics are mean and median')
        elif metric == 'median':
            metric = '50%'
        else:
            pass

        df = self.df.groupby(target_var).describe()

        target_breakdown = df.xs(metric, level=1, axis=1).transpose()
        target_breakdown['delta'] = np.where(target_breakdown[1] - target_breakdown[0] == 0, 0,
                                             ((target_breakdown[1] - target_breakdown[0]) / target_breakdown[0]))

        target_breakdown['delta_abs'] = abs(target_breakdown['delta'])
        target_breakdown.replace([-np.inf, np.inf], 0, inplace=True)
        target_breakdown.sort_values('delta_abs', ascending=False, inplace=True)
        target_breakdown.drop('delta_abs', axis=1, inplace=True)
        target_breakdown = target_breakdown.loc[
            ~target_breakdown['delta'].isin([0, 1])].copy()  # Remove fields with high sub-group cardinality.

        if drop_vars is None:
            pass
        else:
            target_breakdown.drop(drop_vars, inplace=True)

        return target_breakdown.head(top_n).round(3).style.background_gradient(cmap='viridis', subset='delta')

    def plt_feature_dist_by_target(self, fields, target_var):
        # df_melt = pd.melt(df.drop(fields, axis=1).select_dtypes(['int', 'float']), target_var)
        df_melt = pd.melt(self.df[fields].select_dtypes(['int', 'float']), target_var)

        g = sns.FacetGrid(df_melt, col='variable', hue=target_var, col_wrap=4, aspect=1.5, palette='viridis',
                          sharey=False,  # 'tab10',
                          sharex=False, legend_out=False)
        g = g.map(sns.kdeplot, 'value', shade=True)

        g.set_titles('{col_name}', fontsize=4)
        g.set_yticklabels('')
        g.set_xlabels('')

        g.add_legend()
        g.fig.tight_layout()

        self._save_fig()
        return plt.show()

    def bivariate_plot(self, x_var, y_var, x_label, y_label):
        from matplotlib.ticker import FormatStrFormatter

        sns.set_style(style="white")
        gridkw = dict(height_ratios=[4, 3])

        if self.df[x_var].dtype in ('int', 'float'):
            x, edges = pd.cut(self.df[x_var], 10, retbins=True)
        else:
            raise ValueError('Categorical variable currently not supported')

        f, ax = plt.subplots(2, sharex=False, figsize=(14, 8), gridspec_kw=gridkw, constrained_layout=True)

        sns.regplot(x=self.df[x_var], y=self.df[y_var], order=3, scatter=False, x_ci=0.05,
                    ax=ax[0])  # x_estimator=np.mean,
        sns.barplot(x=x, y=self.df[y_var], color='steelblue', ci=None, ax=ax[1])  # df[x_var].round(1)

        #     for p in ax[1].patches:
        #         ax[1].annotate(int(p.get_height()), (p.get_x() + p.get_width() / 2., p.get_height()),
        #                        ha='center', va='center', fontsize=11, color='gray', xytext=(0, 10), textcoords='offset points')

        ax[0].set_xticks([])
        ax[0].set_xlabel('')
        ax[0].set_ylabel(y_label)
        ax[0].xaxis.set_major_formatter(FormatStrFormatter('%0.2f'))
        ax[1].set_xlabel(x_label)
        ax[1].set_ylabel('Volumes')
        ax[1].set_xticklabels(edges.round(1))
        f.suptitle(x_label + ' vs ' + y_label)

        self._save_fig()
        return plt.show()


def minimal_bar(series, ax=None, width=0.8, fisize=(6, 3),
                reorder_yaxis=True, splines_off=True, delete_ticks=True, y_label_large=True, display_value=True):
    if ax is None:
        fig, ax = plt.subplots(figsize=fisize)

    # 1. Delete legend legend=False
    # 2. Tighten the space between bars width=0.8
    series.plot(kind='barh', legend=False, ax=ax, width=width, color='C0');

    # 3. Re-order the y-axis
    if reorder_yaxis:
        ax.invert_yaxis()

    # 4. Delete the square spines
    if splines_off:
        [spine.set_visible(False) for spine in ax.spines.values()]

    # 5. Delete ticks for x and y axis
    # 6. Delete tick label for x axis
    if delete_ticks:
        ax.tick_params(bottom=False, left=False, labelbottom=False)

    # 7. Increase the size of the label for y axis
    if y_label_large:
        ax.tick_params(axis='y', labelsize='x-large')

    # 8. Display each value next to the bar
    if display_value:
        vmax = series.max()
        for i, value in enumerate(series):
            ax.text(value + vmax * 0.02, i, f'{value:,}', fontsize='x-large', va='center', color='C0')
