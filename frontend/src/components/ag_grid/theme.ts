import { themeQuartz } from 'ag-grid-community';

export const myTheme = themeQuartz.withParams({
  accentColor: "#1D5FED",
  backgroundColor: "#111C34",
  borderColor: "#CCC8C829",
  borderRadius: 6,
  browserColorScheme: "dark",
  buttonActiveBorder: true,
  buttonHoverBorder: true,
  cellHorizontalPaddingScale: 1,
  checkboxCheckedBackgroundColor: "#1F51F4",
  chromeBackgroundColor: {
    ref: "foregroundColor",
    mix: 0.07,
    onto: "backgroundColor"
  },
  fontFamily: {
    googleFont: "Roboto"
  },
  fontSize: 14,
  fontWeight: 300,
  foregroundColor: "#FFF",
  headerBackgroundColor: "#232C3E",
  headerFontWeight: 500,
  headerVerticalPaddingScale: 0.9977901786,
  iconSize: 16,
  oddRowBackgroundColor: "#122747",
  spacing: 8,
  tabBarBorder: true,
  wrapperBorderRadius: 8
});