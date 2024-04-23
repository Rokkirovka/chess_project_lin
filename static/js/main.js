const socket = io();

window.cell = null;
window.board_fen = null;

socket.on('update_board', (response) => {
    if (response.path == window.location.pathname){
        if (response.end_game == true){
            $('.end').text(response.result + ' • ' + response.reason)
        }
        print_board(response)
    }
});

socket.on('reload', function() {
    location.reload();
});


function cell_start_drag(id, event) {
    window.cell = id
    $.ajax({url: '', type: 'get', contentType: 'application/json',
        data: {type: 'cell', cell: window.cell, board_fen: window.board_fen}, success: print_board
    })
}


function cell_drag_over(event) {
    event.preventDefault();
}


function cell_drop(id, event) {
    if (window.cell != null){
        let move = window.cell + id;
        $.ajax({
            url: '', type: 'get', contentType: 'application/json',
            data: {type: 'move', move: move, board_fen: window.board_fen}, success: print_board
        })
    }
}


function cell_click(id, event) {
    if (window.cell == null){
        $.ajax({
            url: '', type: 'get', contentType: 'application/json',
            data: {type: 'cell', cell: id, board_fen: window.board_fen}, success: print_board
        })
    }
    else {
        let move = window.cell + id
        window.cell = null
        $.ajax({
            url: '', type: 'get', contentType: 'application/json',
            data: {type: 'move', move: move, board_fen: window.board_fen}, success: print_board
        })
    }
}


function move_click(id) {
    $.ajax({
        url: '', type: 'get', contentType: 'application/json',
        data: {move_number: id},
        success: print_board
    })
}


function print_board(response){
    if ('rate' in response && 'score' in response){
        document.getElementsByClassName('progres-bar-completed')[0].style.height = response.rate + "%";
        $('.rate').text(response.score)
    }
    if ('is_finished' in response && response.is_finished == true){
        $('.end').text(response.result + ' • ' + response.reason)
        $('.analysis-link').text('Анализировать партию')
    }
    for (var cell in response.board){
        $('.chess-board [id=' + response.board[cell].name + '] .cell-piece').text(response.board[cell].piece);
        $('.chess-board [id=' + response.board[cell].name + ']').css('background-color', response.board[cell].color);
    };
    window.board_fen = response.board_fen;
    window.cell = response.current;
}