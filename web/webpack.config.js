const postcss = require('postcss');
var path = require('path');
var TerserPlugin = require('terser-webpack-plugin')

module.exports = {
    entry: './dist/index.js',
    mode: 'development',
    output: {
        filename: 'index.built.js',
        path: path.resolve(__dirname, 'built'),
        publicPath: 'built/'
    },
    module: {
        rules: [
            { test: /\.css$/, use: [
                'style-loader',
                'css-loader',
                {
                    loader: 'postcss-loader',
                    options: {
                        plugins: [
                            postcss.plugin('delete-tilde', function() {
                                return function (css) {
                                    css.walkAtRules('import', function(rule) {
                                        rule.params = rule.params.replace('~', '');
                                    });
                                };
                            }),
                            postcss.plugin('prepend', function() {
                                return function(css) {
                                    css.prepend("@import '@jupyter-widgets/controls/css/labvariables.css';")
                                }
                            }),
                            require('postcss-import')(),
                            require('postcss-preset-env')()
                        ]
                    }
                }
            ]},
            // jquery-ui loads some images
            { test: /\.(jpg|png|gif)$/, use: 'file-loader' },
            // required to load font-awesome
            { test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/, use: 'url-loader?limit=10000&mimetype=application/font-woff' },
            { test: /\.woff(\?v=\d+\.\d+\.\d+)?$/, use: 'url-loader?limit=10000&mimetype=application/font-woff' },
            { test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/, use: 'url-loader?limit=10000&mimetype=application/octet-stream' },
            { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, use: 'file-loader' },
            { test: /\.svg(\?v=\d+\.\d+\.\d+)?$/, use: 'url-loader?limit=10000&mimetype=image/svg+xml' },
            {
                test: /\.less$/,
                use: [{loader: "style-loader"}, {loader: "css-loader" }, {loader: "less-loader" }]
            }
              ]
    },
    optimization: {
        minimizer: [ new TerserPlugin() ]
    }
};
