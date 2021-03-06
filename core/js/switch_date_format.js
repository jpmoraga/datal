String.prototype.replaceAll = function(search, replacement) {
    var target = this;
    return target.split(search).join(replacement);
};

var switchDateFormat;
(function (switchDateFormat) {
    function convert(format, sourceRules, destRules) {
        if (sourceRules == destRules)
            return format;

        var result = '';
        var index = 0;
        var destTokens = getTokens(destRules);
        var sourceMap = getTokenMap(getTokens(sourceRules));
        while (index < format.length) {
            var part = locateNextToken(sourceRules, format, index);
            if (part.literal.length > 0)
                result += destRules.MakeLiteral(part.literal);
            if (part.token.length > 0)
                result += destTokens[sourceMap[part.token]];
            index = part.nextBegin;
        }

        return result;
    }
    switchDateFormat.convert = convert;

    function locateNextToken(rules, format, begin) {
        var literal = '';
        var index = begin;
        var sequence = getTokenSequence(getTokenMap(getTokens(rules)));
        while (index < format.length) {
            var escaped = rules.ReadEscapedPart(format, index);
            if (escaped.length > 0) {
                literal += escaped.value;
                index += escaped.length;
                continue;
            }

            var token;
            for (var i = 0; i < sequence.length; i++) {
                if (format.indexOf(sequence[i], index) == index) {
                    token = sequence[i]
                    break;
                }
            }
            if (!token) {
                literal += format.charAt(index);
                index++;
                continue;
            }

            return {
                token: token,
                literal: literal,
                nextBegin: index + token.length
            };
        }

        return {
            token: '',
            literal: literal,
            nextBegin: index
        };
    }

    function getTokens(rules) {
        return [
            rules.DayOfMonthShort,
            rules.DayOfMonthLong,
            rules.DayOfWeekShort,
            rules.DayOfWeekLong,
            rules.DayOfYearShort,
            rules.DayOfYearLong,
            rules.MonthOfYearShort,
            rules.MonthOfYearLong,
            rules.MonthNameShort,
            rules.MonthNameLong,
            rules.YearShort,
            rules.YearLong,
            rules.AmPm,
            rules.Hour24Short,
            rules.Hour24Long,
            rules.Hour12Short,
            rules.Hour12Long,
            rules.MinuteShort,
            rules.MinuteLong,
            rules.SecondShort,
            rules.SecondLong,
            rules.FractionalSecond1,
            rules.FractionalSecond2,
            rules.FractionalSecond3,
            rules.TimeZone,
            rules.UnixTimestamp
        ].map(function (x) {
            return x || '';
        });
    }

    function getTokenMap(tokens) {
        var map = {};
        for (var i = 0; i < tokens.length; i++) {
            var token = tokens[i];
            if (token) {
                map[token] = i;
            }
        }
        return map;
    }

    function getTokenSequence(map) {
        var tokens = Object.keys(map);
        tokens.sort(function (a, b) {
            return b.length - a.length;
        });
        return tokens;
    }

    function indexOfAny(s, chars) {
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i);
            for (var j = 0; j < chars.length; j++) {
                if (c === chars.charAt(j))
                    return i;
            }
        }
        return -1;
    }

    switchDateFormat.momentJs = {
        DayOfMonthShort: 'D',
        DayOfMonthLong: 'DD',
        DayOfWeekShort: 'ddd',
        DayOfWeekLong: 'dddd',
        DayOfYearShort: 'DDD',
        DayOfYearLong: 'DDDD',
        MonthOfYearShort: 'M',
        MonthOfYearLong: 'MM',
        MonthNameShort: 'MMM',
        MonthNameLong: 'MMMM',
        YearShort: 'YY',
        YearLong: 'YYYY',
        AmPm: 'A',
        Hour24Short: 'H',
        Hour24Long: 'HH',
        Hour12Short: 'h',
        Hour12Long: 'hh',
        MinuteShort: 'm',
        MinuteLong: 'mm',
        SecondShort: 's',
        SecondLong: 'ss',
        FractionalSecond1: 'S',
        FractionalSecond2: 'SS',
        FractionalSecond3: 'SSS',
        TimeZone: 'Z',
        UnixTimestamp: 'X',
        MakeLiteral: function (literal) {
            var reserved = 'MoDdeEwWYgGAaHhmsSzZX';

            literal = literal.replaceAll("[", "(").replaceAll("]", ")");
            if (indexOfAny(literal, reserved) < 0)
                return literal;

            return '[' + literal + ']';
        },
        ReadEscapedPart: function (format, startIndex) {
            if (format.charAt(startIndex) != '[')
                return { value: '', length: 0 };

            var result = '';
            var index = startIndex;
            while (index < format.length) {
                var c = format.charAt(index);

                if (c == ']') {
                    break;
                }

                result += c;
            }

            return {
                value: result,
                length: index - startIndex
            };
        }
    };

    switchDateFormat.datepicker = {
        DayOfMonthShort: 'd',
        DayOfMonthLong: 'dd',
        DayOfWeekShort: 'D',
        DayOfWeekLong: 'DD',
        DayOfYearShort: 'o',
        DayOfYearLong: 'oo',
        MonthOfYearShort: 'm',
        MonthOfYearLong: 'mm',
        MonthNameShort: 'M',
        MonthNameLong: 'MM',
        YearShort: 'y',
        YearLong: 'yy',
        AmPm: null,
        Hour24Short: null,
        Hour24Long: null,
        Hour12Short: null,
        Hour12Long: null,
        MinuteShort: null,
        MinuteLong: null,
        SecondShort: null,
        SecondLong: null,
        FractionalSecond1: null,
        FractionalSecond2: null,
        FractionalSecond3: null,
        TimeZone: null,
        UnixTimestamp: '@',
        MakeLiteral: function (literal) {
            var reserved = "dDomMy@'";
            if (indexOfAny(literal, reserved) < 0)
                return literal;

            return "'" + literal.replaceAll("'", "''") + "'";
        },
        ReadEscapedPart: function (format, startIndex) {
            if (format.charAt(startIndex) != "'")
                return { value: '', length: 0 };

            var result = '';
            var index = startIndex;
            while (++index < format.length) {
                var c = format.charAt(index);

                if (c == "'") {
                    index++;
                    if (index == format.length)
                        break;

                    if (format[index] == "'") {
                        result += c;
                    } else {
                        break;
                    }
                } else {
                    result += c;
                }
            }

            return {
                value: result,
                length: index - startIndex
            };
        }
    };
})(switchDateFormat || (switchDateFormat = {}));

var dp_to_moment = function(pattern) {
    return switchDateFormat.convert(pattern, switchDateFormat.datepicker, switchDateFormat.momentJs);
}