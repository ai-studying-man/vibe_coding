# Source Generated with Decompyle++
# File: �������̺귯��.pyc (Python 3.11)

from win32com.client import GetActiveObject
from win32com.client.gencache import EnsureDispatch
from tkinter import filedialog
import re
from decimal import Decimal
from datetime import datetime, timedelta
import os

def 랜덤정수(최대정수):
    return int.from_bytes(os.urandom(4), byteorder = 'big') % 최대정수


def 랜덤셔플(리스트):
    for i in range(len(리스트) - 1, 0, -1):
        j = 랜덤정수(i)
        리스트[j], 리스트[i] = 리스트[i], 리스트[j]
        return 리스트


class 엑셀:
    엑셀 = None
    엑셀리스트 = None
    
    def 시작(self):
        self.엑셀 = GetActiveObject('Excel.Application')
        return None
    # WARNING: Decompyle incomplete

    
    def 값만붙임(self):
        self.엑셀.Selection.PasteSpecial(Paste = -4163)

    
    def 너비맞춤(self):
        self.엑셀.Selection.Columns.AutoFit()

    
    def 배경색(self, 색상코드):
        self.엑셀.Selection.Interior.Color = 색상코드

    
    def 서식붙임(self):
        self.엑셀.Selection.PasteSpecial(Paste = -4122)

    
    def 취소선(self):
        self.엑셀.Selection.Font.Strikethrough = True

    
    def 각각카운트(self):
        엑셀리스트 = []
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Rows.Count
        열 = 선택범위.Columns.Count
        for i in range(1, 행 + 1):
            for j in range(1, 열 + 1):
                엑셀리스트.append(선택범위.Cells(i, j).Value)
                엑셀리스트 = 엑셀리스트()
                엑셀리스트 = 엑셀리스트()
                카운트리스트 = []
                본거 = []
                for 아이템 in 엑셀리스트:
                    if 아이템 not in 본거:
                        카운트 = 엑셀리스트.count(아이템)
                        카운트리스트.append([
                            아이템,
                            카운트])
                        본거.append(아이템)
                    카운트리스트 = sorted(카운트리스트, key = (lambda x: x[1]), reverse = True)
                    새워크북 = self.엑셀.Workbooks.Add()
                    새워크시트 = 새워크북.Sheets(1)
                    for 행, 줄 in enumerate(카운트리스트, start = 1):
                        for 열, 값 in enumerate(줄, start = 1):
                            새워크시트.Cells(행, 열).Value = 값
                            return None

    
    def 겉바속촉(self):
        self.엑셀.Selection.Borders(7).LineStyle = 1
        self.엑셀.Selection.Borders(8).LineStyle = 1
        self.엑셀.Selection.Borders(9).LineStyle = 1
        self.엑셀.Selection.Borders(10).LineStyle = 1
        self.엑셀.Selection.Borders(11).LineStyle = 1
        self.엑셀.Selection.Borders(12).LineStyle = 1
        self.엑셀.Selection.Borders(7).Weight = -4138
        self.엑셀.Selection.Borders(8).Weight = -4138
        self.엑셀.Selection.Borders(9).Weight = -4138
        self.엑셀.Selection.Borders(10).Weight = -4138
        self.엑셀.Selection.Borders(11).Weight = 2
        self.엑셀.Selection.Borders(12).Weight = 2

    
    def 겉바속점(self):
        self.엑셀.Selection.Borders(7).LineStyle = 1
        self.엑셀.Selection.Borders(8).LineStyle = 1
        self.엑셀.Selection.Borders(9).LineStyle = 1
        self.엑셀.Selection.Borders(10).LineStyle = 1
        self.엑셀.Selection.Borders(11).LineStyle = -4118
        self.엑셀.Selection.Borders(12).LineStyle = -4118
        self.엑셀.Selection.Borders(7).Weight = -4138
        self.엑셀.Selection.Borders(8).Weight = -4138
        self.엑셀.Selection.Borders(9).Weight = -4138
        self.엑셀.Selection.Borders(10).Weight = -4138
        self.엑셀.Selection.Borders(11).Weight = 2
        self.엑셀.Selection.Borders(12).Weight = 2

    
    def 공백정리(self):
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Rows.Count
        열 = 선택범위.Columns.Count
        for i in range(1, 행 + 1):
            for j in range(1, 열 + 1):
                데이터 = 선택범위.Cells(i, j).Value
                if 데이터 != None:
                    데이터 = 데이터.strip()
                    데이터 = re.sub('\\n+', '\n', 데이터)
                    데이터 = re.sub('[ \\t]+', ' ', 데이터)
                    선택범위.Cells(i, j).Value = 데이터
                return None

    
    def 투명표(self):
        self.엑셀.Selection.Borders(7).LineStyle = -4142
        self.엑셀.Selection.Borders(8).LineStyle = -4142
        self.엑셀.Selection.Borders(9).LineStyle = -4142
        self.엑셀.Selection.Borders(10).LineStyle = -4142
        self.엑셀.Selection.Borders(11).LineStyle = -4142
        self.엑셀.Selection.Borders(12).LineStyle = -4142

    
    def 점선표(self):
        self.엑셀.Selection.Borders(7).LineStyle = -4118
        self.엑셀.Selection.Borders(8).LineStyle = -4118
        self.엑셀.Selection.Borders(9).LineStyle = -4118
        self.엑셀.Selection.Borders(10).LineStyle = -4118
        self.엑셀.Selection.Borders(11).LineStyle = -4118
        self.엑셀.Selection.Borders(12).LineStyle = -4118
        self.엑셀.Selection.Borders(7).Weight = 2
        self.엑셀.Selection.Borders(8).Weight = 2
        self.엑셀.Selection.Borders(9).Weight = 2
        self.엑셀.Selection.Borders(10).Weight = 2
        self.엑셀.Selection.Borders(11).Weight = 2
        self.엑셀.Selection.Borders(12).Weight = 2

    
    def 기본표(self):
        self.엑셀.Selection.Borders(7).LineStyle = 1
        self.엑셀.Selection.Borders(8).LineStyle = 1
        self.엑셀.Selection.Borders(9).LineStyle = 1
        self.엑셀.Selection.Borders(10).LineStyle = 1
        self.엑셀.Selection.Borders(11).LineStyle = 1
        self.엑셀.Selection.Borders(12).LineStyle = 1
        self.엑셀.Selection.Borders(7).Weight = 2
        self.엑셀.Selection.Borders(8).Weight = 2
        self.엑셀.Selection.Borders(9).Weight = 2
        self.엑셀.Selection.Borders(10).Weight = 2
        self.엑셀.Selection.Borders(11).Weight = 2
        self.엑셀.Selection.Borders(12).Weight = 2
        self.엑셀.Selection.Borders(7).Color = 0
        self.엑셀.Selection.Borders(8).Color = 0
        self.엑셀.Selection.Borders(9).Color = 0
        self.엑셀.Selection.Borders(10).Color = 0
        self.엑셀.Selection.Borders(11).Color = 0
        self.엑셀.Selection.Borders(12).Color = 0

    
    def 기본테두리(self):
        self.엑셀.Selection.Borders(7).LineStyle = 1
        self.엑셀.Selection.Borders(8).LineStyle = 1
        self.엑셀.Selection.Borders(9).LineStyle = 1
        self.엑셀.Selection.Borders(10).LineStyle = 1
        self.엑셀.Selection.Borders(7).Weight = 2
        self.엑셀.Selection.Borders(8).Weight = 2
        self.엑셀.Selection.Borders(9).Weight = 2
        self.엑셀.Selection.Borders(10).Weight = 2

    
    def 진한테두리(self):
        self.엑셀.Selection.Borders(7).LineStyle = 1
        self.엑셀.Selection.Borders(8).LineStyle = 1
        self.엑셀.Selection.Borders(9).LineStyle = 1
        self.엑셀.Selection.Borders(10).LineStyle = 1
        self.엑셀.Selection.Borders(7).Weight = -4138
        self.엑셀.Selection.Borders(8).Weight = -4138
        self.엑셀.Selection.Borders(9).Weight = -4138
        self.엑셀.Selection.Borders(10).Weight = -4138

    
    def 하단이중선(self):
        self.엑셀.Selection.Borders(9).LineStyle = -4119

    
    def 기본글자(self):
        self.엑셀.Selection.Font.Size = 11
        self.엑셀.Selection.HorizontalAlignment = -4108
        self.엑셀.Selection.VerticalAlignment = -4108
        self.엑셀.Selection.Font.Name = '맑은 고딕'
        self.엑셀.Selection.Font.Color = 0
        self.엑셀.Selection.Font.Bold = False
        self.엑셀.Selection.Font.Italic = False
        self.엑셀.Selection.Font.Underline = False
        self.엑셀.Selection.Font.Strikethrough = False

    
    def 날짜변환(self):
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Rows.Count
        열 = 선택범위.Columns.Count
    # WARNING: Decompyle incomplete

    
    def 랜덤정렬(self):
        if self.엑셀.Selection.Rows.Count > 1:
            선택범위 = self.엑셀.Selection
            데이터 = self.엑셀.selection.Value
            섞인데이터 = list(데이터)
            섞인데이터 = 랜덤셔플(섞인데이터)
            for i, row in enumerate(섞인데이터):
                for j, value in enumerate(row):
                    선택범위.Cells(i + 1, j + 1).Value = value
                    return None
                    return None

    
    def 표시변경(self, 종류 = ('없음',)):
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Rows.Count
        열 = 선택범위.Columns.Count
        for i in range(1, 행 + 1):
            for j in range(1, 열 + 1):
                임시데이터 = 선택범위.Cells(i, j).Text
                if 종류 == '텍스트':
                    선택범위.Cells(i, j).NumberFormat = '@'
                else:
                    선택범위.Cells(i, j).NumberFormatLocal = 'G/표준'
                선택범위.Cells(i, j).Value = 임시데이터
                return None

    
    def 만나이(self):
        선택범위 = self.엑셀.Selection
        행개수 = 선택범위.Rows.Count
        나이 = 0
        for i in range(1, 행개수 + 1):
            나이 = '오류'
            데이터 = 선택범위.Cells(i, 1).Text
            년도 = re.sub('[^0-9]', '', 데이터)
            if len(데이터) == 6:
                년 = int(년도[:2])
                월 = int(년도[2:4])
                일 = int(년도[4:])
                if 년 > datetime.today().year % 100:
                    년 += 1900
                else:
                    년 += 2000
                나이 = datetime.today().year - 년
                if 월 > datetime.today().month:
                    나이 -= 1
                elif 월 == datetime.today().month and 일 > datetime.today().day:
                    나이 -= 1
                elif len(년도) == 8:
                    년 = int(년도[:4])
                    월 = int(년도[4:6])
                    일 = int(년도[6:])
                    나이 = datetime.today().year - 년
                    if 월 > datetime.today().month:
                        나이 -= 1
                    elif 월 == datetime.today().month and 일 > datetime.today().day:
                        나이 -= 1
            선택범위.Cells(i, 2).Value = 나이
            return None

    
    def 맑은고딕(self, 크기, 진하게, 색상 = (0, 0, 0)):
        self.엑셀.Selection.Font.Name = '맑은 고딕'
        self.엑셀.Selection.Font.Bold = False
        if 크기 != 0:
            self.엑셀.Selection.Font.Size = 크기
        if 진하게 == 1:
            self.엑셀.Selection.Font.Bold = True
        self.엑셀.Selection.Font.Color = 색상

    
    def 병합해제(self):
        기준시트 = self.엑셀.ActiveSheet
        시작행 = self.엑셀.Selection.Row
        마지막행 = 기준시트.UsedRange.Rows.Count + 기준시트.UsedRange.Row + 3
        마지막열 = 기준시트.UsedRange.Columns.Count + 1
        기준시트.Range(기준시트.Cells(시작행, 1), 기준시트.Cells(마지막행, 마지막열)).UnMerge()

    
    def 산출근거계산(self):
        선택범위 = self.엑셀.Selection
        행개수 = 선택범위.Rows.Count
    # WARNING: Decompyle incomplete

    
    def 순번(self):
        선택범위 = self.엑셀.Selection
        self.엑셀.Selection.NumberFormatLocal = 'G/표준'
        행 = self.엑셀.Selection.Row
        기준값 = 1
        if 선택범위.Cells(1, 1).Value != None and isinstance(선택범위.Cells(1, 1).Value, (int, float)) and Decimal(선택범위.Cells(1, 1).Value) % 1 == 0:
            기준값 = Decimal(선택범위.Cells(1, 1).Value)
        행개수 = 선택범위.Rows.Count
        for i in range(1, 행개수 + 1):
            선택범위.Cells(i, 1).Formula = f'''=Row()-{행}+{기준값}'''
            return None

    
    def 순환복사(self):
        self.엑셀리스트 = []
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Rows.Count
        열 = 선택범위.Columns.Count
        for i in range(1, 행 + 1):
            for j in range(1, 열 + 1):
                self.엑셀리스트.append(선택범위.Cells(i, j).Value)
                self.엑셀리스트 = self.엑셀리스트()
                return None

    
    def 순환붙임(self):
        self.엑셀리스트
        선택범위 = self.엑셀.Selection
        임시주소목록 = []
        for 셀 in 선택범위:
            임시주소 = ''
            if 셀.MergeCells:
                임시주소 = 셀.MergeArea.Address
            else:
                임시주소 = 셀.Address
            if 임시주소 not in 임시주소목록:
                임시주소목록.append(임시주소)
            for i in range(0, min(len(self.엑셀리스트), len(임시주소목록))):
                self.엑셀.ActiveSheet.Range(임시주소목록[i]).Value = self.엑셀리스트[i]
                return None

    
    def 숫자만(self, 종류 = ('없음',)):
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Rows.Count
        열 = 선택범위.Columns.Count
        for i in range(1, 행 + 1):
            for j in range(1, 열 + 1):
                데이터 = 선택범위.Cells(i, j).Value
                데이터 = str(데이터)
                if re.search('\\d', 데이터):
                    여부 = re.search('\\d+(천|백만)', 데이터)
                    데이터 = re.sub('[^0-9\\.\\-]', '', 데이터)
                    if 여부 and 여부.group(1) == '천':
                        pass
                    elif 여부 and 여부.group(1) == '백만':
                        pass
                    
                    곱할값 = 1
                    데이터 = Decimal(데이터) if '.' in 데이터 else int(데이터)
                    데이터 = 데이터 * 곱할값
                    if 종류 == '천원':
                        데이터 = str(int(round(데이터 / 1000, 0))) + '천원'
                    if 종류 == '백만원':
                        데이터 = str(int(round(데이터 / 1000000, 0))) + '백만원'
                    선택범위.Cells(i, j).Value = str(데이터)
                    선택범위.Cells(i, j).NumberFormat = '#,##0'
                return None

    
    def 아래전부개수세기(self):
        기준시트 = self.엑셀.ActiveSheet
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Row
        기준행수 = self.엑셀.ActiveSheet.UsedRange.Rows.Count + 선택범위.Row + 3
        열 = 선택범위.Column
        열수 = 선택범위.Columns.Count
        for i in range(1, 열수 + 1):
            선택범위.Cells(1, i).Formula = f'''=Subtotal(3,{선택범위.Cells(2, i).Address}:{선택범위.Cells(기준행수, i).Address})'''
            return None

    
    def 아래전부합치기(self):
        기준시트 = self.엑셀.ActiveSheet
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Row
        기준행수 = self.엑셀.ActiveSheet.UsedRange.Rows.Count + 선택범위.Row + 3
        열 = 선택범위.Column
        열수 = 선택범위.Columns.Count
        for i in range(1, 열수 + 1):
            선택범위.Cells(1, i).Formula = f'''=Subtotal(9,{선택범위.Cells(2, i).Address}:{선택범위.Cells(기준행수, i).Address})'''
            return None

    
    def 아래전부평균값(self):
        기준시트 = self.엑셀.ActiveSheet
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Row
        기준행수 = self.엑셀.ActiveSheet.UsedRange.Rows.Count + 선택범위.Row + 3
        열 = 선택범위.Column
        열수 = 선택범위.Columns.Count
        for i in range(1, 열수 + 1):
            선택범위.Cells(1, i).Formula = f'''=Subtotal(1,{선택범위.Cells(2, i).Address}:{선택범위.Cells(기준행수, i).Address})'''
            return None

    
    def 아래전부중위값(self):
        기준시트 = self.엑셀.ActiveSheet
        선택범위 = self.엑셀.Selection
        행 = 선택범위.Row
        기준행수 = self.엑셀.ActiveSheet.UsedRange.Rows.Count + 선택범위.Row + 3
        열 = 선택범위.Column
        열수 = 선택범위.Columns.Count
        for i in range(1, 열수 + 1):
            선택범위.Cells(1, i).Formula = f'''=Median({선택범위.Cells(2, i).Address}:{선택범위.Cells(기준행수, i).Address})'''
            return None

    
    def 예시글자(self):
        self.엑셀.Selection.Font.Size = 11
        self.엑셀.Selection.HorizontalAlignment = -4108
        self.엑셀.Selection.VerticalAlignment = -4108
        self.엑셀.Selection.Font.Name = '맑은 고딕'
        self.엑셀.Selection.Font.Color = 12874308
        self.엑셀.Selection.Font.Bold = False
        self.엑셀.Selection.Font.Italic = True
        self.엑셀.Selection.Font.Underline = False
        self.엑셀.Selection.Font.Strikethrough = False

    
    def 인쇄범위(self):
        기준시트 = self.엑셀.ActiveSheet
        기준열 = 기준시트.UsedRange.Column
        기준행 = 기준시트.UsedRange.Row
        기준열수 = 기준시트.UsedRange.Columns.Count
        기준행수 = 기준시트.UsedRange.Rows.Count
        기준시트.PageSetup.PrintArea = f'''{기준시트.Cells(1, 1).Address}:{기준시트.Cells(기준행 + 기준행수 - 1, 기준열 + 기준열수 - 1).Address}'''
        기준시트.PageSetup.FitToPagesWide = 1
        기준시트.PageSetup.FitToPagesTall = False
        self.엑셀.ActiveWindow.View = 2
        기준시트.DisplayPageBreaks = True

    
    def 기본화면(self):
        기준시트 = self.엑셀.ActiveSheet
        self.엑셀.ActiveWindow.View = 1
        기준시트.DisplayPageBreaks = False

    
    def 전부해제(self):
        self.엑셀.ActiveSheet.Unprotect()
    # WARNING: Decompyle incomplete

    
    def 제목(self):
        self.엑셀.Selection.Merge()
        self.엑셀.Selection.Font.Size = 20
        self.엑셀.Selection.HorizontalAlignment = -4108
        self.엑셀.Selection.VerticalAlignment = -4108
        self.엑셀.Selection.Font.Name = '맑은 고딕'
        self.엑셀.Selection.Font.Bold = True
        self.엑셀.Selection.Font.Italic = False
        self.엑셀.Selection.Font.Underline = False

    
    def 직제순정렬(self):
        행 = self.엑셀.Selection.Row
        열 = self.엑셀.Selection.Column
        행개수 = self.엑셀.Selection.Rows.Count
        열개수 = self.엑셀.Selection.Columns.Count
        두번째열부터 = self.엑셀.ActiveSheet.Range(self.엑셀.ActiveSheet.Cells(행, 열 + 1), self.엑셀.ActiveSheet.Cells(행 + 행개수 - 1, 열 + 열개수 - 1))
        첫번째열 = self.엑셀.Selection.Columns(1)
        리스트 = 첫번째열.Value
        리스트 = 리스트()
        리스트 = 리스트()
        self.엑셀.ActiveSheet.Sort.SortFields.Clear()
        self.엑셀.ActiveSheet.Sort.SortFields.Add(Key = 두번째열부터.Columns(1), SortOn = 0, Order = 1, CustomOrder = ','.join(리스트), DataOption = 0)
        self.엑셀.ActiveSheet.Sort.SetRange(두번째열부터)
        self.엑셀.ActiveSheet.Sort.Header = 0
        self.엑셀.ActiveSheet.Sort.MatchCase = False
        self.엑셀.ActiveSheet.Sort.Orientation = 1
        self.엑셀.ActiveSheet.Sort.Apply()

    
    def 취합(self, 행수 = (4,)):
        기준시트 = self.엑셀.ActiveSheet
        파일들 = filedialog.askopenfilenames(title = 'Open File', filetypes = [
            ('Excel Files', '*.xlsx *.xls')])
        기준행 = 기준시트.Cells(self.엑셀.ActiveSheet.Rows.Count, 2).End(-4162).Row + 1
        기준열 = 기준시트.UsedRange.Columns.Count + 1
        for 파일경로 in 파일들:
            임시파일 = self.엑셀.Workbooks.Open(파일경로)
            임시시트 = 임시파일.Sheets(1)
            마지막행 = 임시시트.Cells(임시시트.Rows.Count, 2).End(-4162).Row
            임시시트.Range(임시시트.Cells(행수, 1), 임시시트.Cells(마지막행, 기준열)).Copy()
            기준시트.Cells(기준행, 1).PasteSpecial(Paste = -4163)
            임시파일.Close(SaveChanges = False)
            기준행 = 기준시트.Cells(self.엑셀.ActiveSheet.Rows.Count, 2).End(-4162).Row + 1
            return None

    
    def 항목서식(self):
        self.엑셀.Selection.Font.Size = 11
        self.엑셀.Selection.HorizontalAlignment = -4108
        self.엑셀.Selection.VerticalAlignment = -4108
        self.엑셀.Selection.Font.Name = '맑은 고딕'
        self.엑셀.Selection.Font.Bold = True
        self.엑셀.Selection.Font.Italic = False
        self.엑셀.Selection.Font.Underline = False
        self.엑셀.Selection.Interior.Color = 65535

    
    def 행제거(self, 열번호 = (2,)):
        기준시트 = self.엑셀.ActiveSheet
        끝행 = self.엑셀.Selection.Row
        시작행 = 기준시트.UsedRange.Rows(기준시트.UsedRange.Rows.Count).Row
    # WARNING: Decompyle incomplete


