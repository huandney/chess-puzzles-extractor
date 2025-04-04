import chess
import chess.engine

ALT_THRESHOLD = 25  # diferença máxima (em cp) para considerar lances equivalentes (0.25 peão)
PUZZLE_UNICITY_THRESHOLD = 150  # margem mínima para próximo lance pior (1.5 peão)

def find_alternatives(engine, board, solver_color, max_variants):
    """
    Analisa a posição dada (lado solver_color para jogar) e retorna o melhor lance e alternativas dentro de ALT_THRESHOLD.
    Retorna {"best": Move, "alternatives": [Move, ...]} ou None se houver mais alternativas do que max_variants permite.
    """
    # Definir número de PVs a pedir: max_variants+2 para detectar excesso
    requested_pv = max_variants + 1
    requested_pv_excess = max_variants + 2
    try:
        info_list = engine.analyse(board, limit=chess.engine.Limit(depth=18), multipv=requested_pv_excess)
    except chess.engine.EngineError:
        # Fallback: análise single PV se multipv falhar
        try:
            best = engine.analyse(board, limit=chess.engine.Limit(depth=18))
            if not best:
                return None
            info_list = [best]
        except Exception:
            return None

    # Garantir que info_list seja uma lista
    if isinstance(info_list, dict):
        info_list = [info_list]
    if not info_list:
        return None

    # Extrair pontuações do ponto de vista de solver_color
    scores = []
    for info in info_list:
        score = info.get("score")
        if score is None:
            continue
        # Converter score para centipawn na perspectiva de solver_color
        if score.is_mate():
            mate_plies = score.pov(solver_color).mate()
            if mate_plies is None:
                cp_val = 0
            elif mate_plies > 0:
                cp_val = -100000  # mate contra o solver (derrota)
            else:
                cp_val = 100000   # mate a favor do solver (vitória)
        else:
            cp = score.pov(solver_color).score()
            cp_val = cp if cp is not None else 0
        scores.append(cp_val)
    if not scores:
        return None

    # Identificar melhores lances dentro do threshold
    best_score = scores[0]
    candidates_moves = []
    for idx, sc in enumerate(scores):
        if best_score - sc <= ALT_THRESHOLD:
            pv_line = info_list[idx].get("pv")
            if pv_line:
                move = pv_line[0]
            else:
                continue  # ignora caso não haja PV completa
            candidates_moves.append(move)
        else:
            break  # restante já fora do ALT_THRESHOLD (lista está ordenada)
    # Se número de movimentos equivalentes excede max_variants+1, considerar puzzle ambíguo
    if len(candidates_moves) > max_variants + 1:
        return None
    if not candidates_moves:
        return None

    # Verificar unicidade do melhor lance em relação ao próximo fora do cluster
    best_move = candidates_moves[0]
    alt_moves = candidates_moves[1:]
    # Se variantes extras são permitidas, exigir que próximo lance fora do top N seja muito inferior (>=150 cp)
    if max_variants > 0:
        if len(scores) > len(candidates_moves):
            next_score = scores[len(candidates_moves)]
            if best_score - next_score < PUZZLE_UNICITY_THRESHOLD:
                return None
    else:
        # max_variants = 0: exigir que melhor lance seja claramente superior ao segundo melhor
        if len(scores) >= 2 and (best_score - scores[1] < PUZZLE_UNICITY_THRESHOLD):
            return None

    return {"best": best_move, "alternatives": alt_moves}
